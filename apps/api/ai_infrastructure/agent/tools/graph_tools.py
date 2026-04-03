"""
LangChain tools that wrap GraphTraversalService.

These are the agent's eyes into the graph structure.
All tools are READ-ONLY — they never mutate the graph.
"""

from langchain.tools import BaseTool, tool
from sqlmodel import Session
from uuid import UUID
from typing import List


def get_graph_traversal_tools(session: Session, graph_id: UUID) -> List[BaseTool]:
    """
    Factory: returns a list of LangChain tools bound to a specific
    session + graph_id. Call once per request.
    """
    from apps.api.ai_infrastructure.graph.graph_traversal import GraphTraversalService

    svc = GraphTraversalService(session, graph_id)

    # ── Tool 1: find a node by name ──────────────────────────────────

    @tool("find_node_by_name", return_direct=False)
    def find_node_by_name(node_name: str) -> str:
        """
        Find an infrastructure node by its name.
        Use this FIRST to resolve a human-readable name (like 'API Gateway'
        or 'Redis') into its node details before calling other graph tools.
        Returns the node's id, key, name, category, and properties.
        """
        # Try exact match first
        node = svc.find_node(node_name)
        if node:
            return _format_node(node)

        # Fall back to fuzzy
        matches = svc.find_nodes_fuzzy(node_name)
        if not matches:
            return f"No node found matching '{node_name}'. Try a different name."
        if len(matches) == 1:
            return _format_node(matches[0])

        names = ", ".join(m["name"] for m in matches)
        return f"Multiple nodes match '{node_name}': {names}. Please be more specific."

    # ── Tool 2: get neighbors ────────────────────────────────────────

    @tool("get_neighbors", return_direct=False)
    def get_neighbors(node_name: str, direction: str = "both") -> str:
        """
        Get the direct neighbors of a node.
        Inputs:
        - node_name: the name of the node (e.g. 'API Gateway')
        - direction: 'upstream' (what feeds INTO this node),
                     'downstream' (what this node feeds INTO),
                     or 'both' (default)
        """
        node = svc.find_node(node_name)
        if not node:
            return f"Node '{node_name}' not found."

        neighbors = svc.get_neighbors(
            UUID(node["id"]),
            direction=direction if direction in ("upstream", "downstream", "both") else "both",
        )
        if not neighbors:
            return f"Node '{node['name']}' has no {direction} neighbors."

        lines = [f"**Neighbors of '{node['name']}' ({direction}):**"]
        for n in neighbors:
            rel = n.get("relationship", "")
            lines.append(f"  • {n['name']} ({n['category']}) [{rel}]")
        return "\n".join(lines)

    # ── Tool 3: dependency chain ─────────────────────────────────────

    @tool("get_dependency_chain", return_direct=False)
    def get_dependency_chain(node_name: str, max_depth: int = 5) -> str:
        """
        Walk the DOWNSTREAM dependency chain of a node transitively.
        Shows everything this node depends on, up to max_depth hops.
        Use for questions like 'What does X depend on?'
        """
        node = svc.find_node(node_name)
        if not node:
            return f"Node '{node_name}' not found."

        result = svc.get_dependency_chain(UUID(node["id"]), max_depth=max_depth)
        if not result["nodes"]:
            return f"Node '{node['name']}' has no downstream dependencies."

        lines = [f"**Dependency chain for '{result['root']['name']}' ({result['total']} nodes):**"]
        for n in result["nodes"]:
            indent = "  " * n.get("depth", 1)
            lines.append(f"{indent}└─ {n['name']} ({n['category']}) [depth {n.get('depth', '?')}]")
        return "\n".join(lines)

    # ── Tool 4: impact radius ────────────────────────────────────────

    @tool("get_impact_radius", return_direct=False)
    def get_impact_radius(node_name: str, max_depth: int = 5) -> str:
        """
        Reverse dependency walk — find everything that depends on this node.
        Use for questions like 'What breaks if X goes down?' or
        'What is the blast radius of X?'
        """
        node = svc.find_node(node_name)
        if not node:
            return f"Node '{node_name}' not found."

        result = svc.get_impact_radius(UUID(node["id"]), max_depth=max_depth)
        if not result["nodes"]:
            return f"Nothing depends on '{node['name']}'."

        lines = [f"**Impact radius for '{result['root']['name']}' ({result['total']} affected nodes):**"]
        for n in result["nodes"]:
            indent = "  " * n.get("depth", 1)
            lines.append(f"{indent}└─ {n['name']} ({n['category']}) [depth {n.get('depth', '?')}]")
        return "\n".join(lines)

    # ── Tool 5: find paths between two nodes ─────────────────────────

    @tool("find_paths_between", return_direct=False)
    def find_paths_between(source_name: str, target_name: str) -> str:
        """
        Find all paths between two nodes in the architecture graph.
        Use for questions like 'How does X connect to Y?' or
        'What is the path from X to Y?'
        """
        source = svc.find_node(source_name)
        if not source:
            return f"Source node '{source_name}' not found."
        target = svc.find_node(target_name)
        if not target:
            return f"Target node '{target_name}' not found."

        paths = svc.find_paths(UUID(source["id"]), UUID(target["id"]))
        if not paths:
            return f"No paths found from '{source['name']}' to '{target['name']}'."

        lines = [f"**{len(paths)} path(s) from '{source['name']}' to '{target['name']}':**"]
        for i, path in enumerate(paths, 1):
            path_str = " → ".join(n["name"] for n in path)
            lines.append(f"  Path {i}: {path_str}")
        return "\n".join(lines)

    # ── Return all tools ─────────────────────────────────────────────

    return [
        find_node_by_name,
        get_neighbors,
        get_dependency_chain,
        get_impact_radius,
        find_paths_between,
    ]


def _format_node(node: dict) -> str:
    """Render a node dict as human-readable text for the LLM."""
    lines = [
        f"**Node: {node['name']}**",
        f"  ID: {node['id']}",
        f"  Key: {node['key']}",
        f"  Category: {node['category']}",
    ]
    props = {k: v for k, v in node.get("properties", {}).items()
             if k not in ("category", "label")}
    if props:
        lines.append("  Properties:")
        for k, v in props.items():
            lines.append(f"    • {k}: {v}")
    return "\n".join(lines)
