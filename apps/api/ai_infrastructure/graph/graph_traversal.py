"""
GraphTraversalService — SQL-based graph walks against Node/Edge tables.

This is the READ-ONLY graph intelligence layer. It queries the live
PostgreSQL graph directly (no vector DB, no embeddings) to answer
structural and relational questions:
  - "What depends on X?"
  - "What breaks if X goes down?"
  - "How does X connect to Y?"
"""

from typing import List, Dict, Any, Optional, Literal
from uuid import UUID
from collections import deque

from sqlmodel import Session, select
from sqlalchemy import or_, func

from apps.api.models import Node, Edge


class GraphTraversalService:
    """
    Pure traversal primitives over the Opscribe Node/Edge schema.
    Every method returns plain dicts — no ORM objects leak out.
    """

    def __init__(self, session: Session, graph_id: UUID):
        self.session = session
        self.graph_id = graph_id

    # ------------------------------------------------------------------ #
    #  Node lookup                                                        #
    # ------------------------------------------------------------------ #

    def find_node(self, name: str) -> Optional[Dict[str, Any]]:
        """Case-insensitive lookup by display_name or key."""
        stmt = (
            select(Node)
            .where(Node.graph_id == self.graph_id)
            .where(
                or_(
                    func.lower(Node.display_name) == name.lower(),
                    func.lower(Node.key) == name.lower(),
                )
            )
        )
        node = self.session.exec(stmt).first()
        return self._node_to_dict(node) if node else None

    def find_nodes_fuzzy(self, name: str) -> List[Dict[str, Any]]:
        """Fuzzy search — returns all nodes whose name contains the query."""
        pattern = f"%{name.lower()}%"
        stmt = (
            select(Node)
            .where(Node.graph_id == self.graph_id)
            .where(
                or_(
                    func.lower(Node.display_name).like(pattern),
                    func.lower(Node.key).like(pattern),
                )
            )
        )
        return [self._node_to_dict(n) for n in self.session.exec(stmt).all()]

    # ------------------------------------------------------------------ #
    #  Neighbors                                                          #
    # ------------------------------------------------------------------ #

    def get_neighbors(
        self,
        node_id: UUID,
        direction: Literal["upstream", "downstream", "both"] = "both",
    ) -> List[Dict[str, Any]]:
        """
        Get direct neighbors of a node.
          - downstream = nodes this node points TO   (from_node_id = node_id)
          - upstream   = nodes that point TO this node (to_node_id = node_id)
        """
        neighbors: List[Dict[str, Any]] = []

        if direction in ("downstream", "both"):
            stmt = (
                select(Node)
                .join(Edge, Edge.to_node_id == Node.id)
                .where(Edge.graph_id == self.graph_id)
                .where(Edge.from_node_id == node_id)
            )
            for n in self.session.exec(stmt).all():
                d = self._node_to_dict(n)
                d["relationship"] = "downstream"
                neighbors.append(d)

        if direction in ("upstream", "both"):
            stmt = (
                select(Node)
                .join(Edge, Edge.from_node_id == Node.id)
                .where(Edge.graph_id == self.graph_id)
                .where(Edge.to_node_id == node_id)
            )
            for n in self.session.exec(stmt).all():
                d = self._node_to_dict(n)
                d["relationship"] = "upstream"
                neighbors.append(d)

        return neighbors

    # ------------------------------------------------------------------ #
    #  Dependency chain  (BFS downstream)                                 #
    # ------------------------------------------------------------------ #

    def get_dependency_chain(
        self, node_id: UUID, max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        BFS walk of transitive DOWNSTREAM dependencies.
        Returns a tree structure: { node, depth, children: [...] }
        """
        return self._bfs_walk(node_id, max_depth, direction="downstream")

    # ------------------------------------------------------------------ #
    #  Impact radius  (BFS upstream — reverse deps)                       #
    # ------------------------------------------------------------------ #

    def get_impact_radius(
        self, node_id: UUID, max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Reverse BFS — "what depends on me?"
        Walks UPSTREAM to find everything that would be affected.
        """
        return self._bfs_walk(node_id, max_depth, direction="upstream")

    # ------------------------------------------------------------------ #
    #  All paths between two nodes                                        #
    # ------------------------------------------------------------------ #

    def find_paths(
        self,
        source_id: UUID,
        target_id: UUID,
        max_depth: int = 6,
    ) -> List[List[Dict[str, Any]]]:
        """
        Find ALL paths between source and target (DFS, capped at max_depth).
        Returns list of paths, each path is a list of node dicts.
        """
        paths: List[List[Dict[str, Any]]] = []
        source_node = self.session.get(Node, source_id)
        if not source_node:
            return paths

        self._dfs_paths(
            current_id=source_id,
            target_id=target_id,
            visited=set(),
            current_path=[self._node_to_dict(source_node)],
            paths=paths,
            depth=0,
            max_depth=max_depth,
        )
        return paths

    # ------------------------------------------------------------------ #
    #  Subgraph extraction                                                #
    # ------------------------------------------------------------------ #

    def get_subgraph(
        self, node_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Return the nodes and all interconnecting edges for a set of node IDs."""
        id_set = set(node_ids)

        nodes = self.session.exec(
            select(Node)
            .where(Node.graph_id == self.graph_id)
            .where(Node.id.in_(node_ids))  # type: ignore[attr-defined]
        ).all()

        edges = self.session.exec(
            select(Edge)
            .where(Edge.graph_id == self.graph_id)
            .where(Edge.from_node_id.in_(node_ids))  # type: ignore[attr-defined]
            .where(Edge.to_node_id.in_(node_ids))    # type: ignore[attr-defined]
        ).all()

        return {
            "nodes": [self._node_to_dict(n) for n in nodes],
            "edges": [self._edge_to_dict(e) for e in edges],
        }

    # ================================================================== #
    #  Private helpers                                                    #
    # ================================================================== #

    def _bfs_walk(
        self,
        start_id: UUID,
        max_depth: int,
        direction: Literal["upstream", "downstream"],
    ) -> Dict[str, Any]:
        """Generic BFS in either direction. Returns a flat list with depth info."""
        start_node = self.session.get(Node, start_id)
        if not start_node:
            return {"root": None, "nodes": [], "total": 0}

        visited: set[UUID] = {start_id}
        queue: deque[tuple[UUID, int]] = deque([(start_id, 0)])
        result_nodes: List[Dict[str, Any]] = []

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            # Get next-hop edges
            if direction == "downstream":
                stmt = select(Edge).where(
                    Edge.graph_id == self.graph_id,
                    Edge.from_node_id == current_id,
                )
            else:  # upstream
                stmt = select(Edge).where(
                    Edge.graph_id == self.graph_id,
                    Edge.to_node_id == current_id,
                )

            edges = self.session.exec(stmt).all()

            for edge in edges:
                next_id = edge.to_node_id if direction == "downstream" else edge.from_node_id
                if next_id not in visited:
                    visited.add(next_id)
                    next_node = self.session.get(Node, next_id)
                    if next_node:
                        node_dict = self._node_to_dict(next_node)
                        node_dict["depth"] = depth + 1
                        node_dict["via_edge"] = self._edge_to_dict(edge)
                        result_nodes.append(node_dict)
                        queue.append((next_id, depth + 1))

        return {
            "root": self._node_to_dict(start_node),
            "nodes": result_nodes,
            "total": len(result_nodes),
        }

    def _dfs_paths(
        self,
        current_id: UUID,
        target_id: UUID,
        visited: set,
        current_path: List[Dict[str, Any]],
        paths: List[List[Dict[str, Any]]],
        depth: int,
        max_depth: int,
    ) -> None:
        """DFS to find all paths. Mutates `paths` in place."""
        if current_id == target_id and depth > 0:
            paths.append(list(current_path))
            return
        if depth >= max_depth:
            return

        visited.add(current_id)

        # Walk downstream edges
        edges = self.session.exec(
            select(Edge).where(
                Edge.graph_id == self.graph_id,
                Edge.from_node_id == current_id,
            )
        ).all()

        for edge in edges:
            next_id = edge.to_node_id
            if next_id not in visited:
                next_node = self.session.get(Node, next_id)
                if next_node:
                    current_path.append(self._node_to_dict(next_node))
                    self._dfs_paths(
                        next_id, target_id, visited,
                        current_path, paths, depth + 1, max_depth,
                    )
                    current_path.pop()

        visited.discard(current_id)

    @staticmethod
    def _node_to_dict(node: Node) -> Dict[str, Any]:
        """Serialize a Node to a clean dict (no ORM noise, no UI coords)."""
        ignored = {"position", "x", "y", "icon", "color", "categoryColor",
                    "bg", "width", "height", "selected", "dragging", "z", "zIndex"}
        props = {}
        if node.properties:
            props = {k: v for k, v in node.properties.items() if k not in ignored}

        return {
            "id": str(node.id),
            "key": node.key,
            "name": node.display_name or node.key,
            "category": props.get("category", "Infrastructure"),
            "properties": props,
        }

    @staticmethod
    def _edge_to_dict(edge: Edge) -> Dict[str, Any]:
        """Serialize an Edge to a clean dict."""
        return {
            "id": str(edge.id),
            "from_node_id": str(edge.from_node_id),
            "to_node_id": str(edge.to_node_id),
            "edge_type_id": str(edge.edge_type_id),
            "properties": edge.properties or {},
        }
