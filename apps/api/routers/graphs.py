from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select, delete as sql_delete
from typing import List
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Graph, Node, Edge, NodeType, EdgeType
from apps.api import schemas
from apps.api.schemas import GraphSyncUpdate
from apps.api.ai_infrastructure.rag.embedding_sync import re_embed_graph
from apps.api.ai_infrastructure.rag.models import KnowledgeBaseItem

router = APIRouter(
    prefix="/graphs",
    tags=["graphs"]
)

@router.post("/", response_model=schemas.GraphRead)
def create_graph(graph: schemas.GraphCreate, session: Session = Depends(get_session)):
    db_graph = Graph.model_validate(graph)
    session.add(db_graph)
    session.commit()
    session.refresh(db_graph)
    return db_graph

@router.get("/{graph_id}", response_model=schemas.GraphRead)
def read_graph(graph_id: UUID, session: Session = Depends(get_session)):
    graph = session.get(Graph, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    return graph

@router.get("/{graph_id}/visualize", response_model=schemas.GraphVisualization)
def visualize_graph(graph_id: UUID, session: Session = Depends(get_session)):
    """
    Returns all nodes and edges for a given graph, optimized for frontend visualization.
    """
    graph = session.get(Graph, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    # Fetch all nodes in the graph
    nodes = session.exec(select(Node).where(Node.graph_id == graph_id)).all()
    
    # Fetch all edges in the graph
    edges = session.exec(select(Edge).where(Edge.graph_id == graph_id)).all()
    
    return schemas.GraphVisualization(
        nodes=nodes,
        edges=edges
    )

@router.put("/{graph_id}/sync", response_model=schemas.GraphRead)
def sync_graph(
    graph_id: UUID,
    body: GraphSyncUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """
    Sync graph with frontend payload: update name, then replace nodes and edges
    with the given lists. Creates default NodeType/EdgeType for the graph if needed.
    """
    graph = session.get(Graph, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")

    if body.name is not None:
        graph.name = body.name
        session.add(graph)

    # Get or create a single NodeType and EdgeType for this graph
    node_type = session.exec(
        select(NodeType).where(
            NodeType.graph_id == graph_id,
            NodeType.name == "Infrastructure",
        )
    ).first()
    if not node_type:
        node_type = NodeType(
            client_id=graph.client_id,
            graph_id=graph_id,
            name="Infrastructure",
            category=None,
            allowed_properties=[],
        )
        session.add(node_type)
        session.flush()

    edge_type = session.exec(
        select(EdgeType).where(
            EdgeType.graph_id == graph_id,
            EdgeType.name == "connects",
        )
    ).first()
    if not edge_type:
        edge_type = EdgeType(
            client_id=graph.client_id,
            graph_id=graph_id,
            name="connects",
        )
        session.add(edge_type)
        session.flush()

    # Clear all edges first to prevent ORM cascade issues when deleting nodes
    for edge in session.exec(select(Edge).where(Edge.graph_id == graph_id)).all():
        session.delete(edge)
    session.flush()

    payload_keys = {n.id for n in body.nodes}

    # Remove nodes that are no longer in the payload
    existing_nodes = session.exec(select(Node).where(Node.graph_id == graph_id)).all()
    for node in existing_nodes:
        if node.key not in payload_keys:
            session.delete(node)
    session.flush()

    # Upsert nodes
    for n in body.nodes:
        data = n.data or {}
        display_name = data.get("label") or n.id
        properties = {**data, "position": n.position}
        existing = session.exec(
            select(Node).where(
                Node.graph_id == graph_id,
                Node.key == n.id,
            )
        ).first()
        if existing:
            existing.display_name = display_name
            existing.properties = properties
            session.add(existing)
        else:
            session.add(
                Node(
                    client_id=graph.client_id,
                    graph_id=graph_id,
                    node_type_id=node_type.id,
                    key=n.id,
                    display_name=display_name,
                    properties=properties,
                    source="ui",
                )
            )
    session.flush()

    # Build key -> node id map
    key_to_node = {
        node.key: node.id
        for node in session.exec(select(Node).where(Node.graph_id == graph_id)).all()
    }

    # Edges from payload
    for e in body.edges:
        from_id = key_to_node.get(e.source)
        to_id = key_to_node.get(e.target)
        if from_id and to_id:
            session.add(
                Edge(
                    client_id=graph.client_id,
                    graph_id=graph_id,
                    edge_type_id=edge_type.id,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    properties={},
                )
            )

    session.commit()
    session.refresh(graph)
    background_tasks.add_task(re_embed_graph, graph_id)
    return graph


@router.delete("/{graph_id}")
def delete_graph(graph_id: UUID, session: Session = Depends(get_session)):
    graph = session.get(Graph, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    # Clean up vector store entries for this graph
    session.exec(sql_delete(KnowledgeBaseItem).where(KnowledgeBaseItem.graph_id == graph_id))
    session.delete(graph)
    session.commit()
    return {"ok": True}

# --- NodeType and EdgeType endpoints as sub-resources of graphs implies context ---
# For simplicity, we can add them here or in separate routers. 
# Let's add simple CRUD for types here specific to a graph if needed, 
# but usually types might be re-used. 
# The prompt asks for "add nodes/edges/graphs per client id".
# We will assume NodeTypes/EdgeTypes are created separately or needed before creating nodes.
# Let's add basic endpoints for them.

@router.post("/node-types/", response_model=schemas.NodeTypeRead)
def create_node_type(node_type: schemas.NodeTypeCreate, session: Session = Depends(get_session)):
    db_node_type = NodeType.model_validate(node_type)
    session.add(db_node_type)
    session.commit()
    session.refresh(db_node_type)
    return db_node_type

@router.post("/edge-types/", response_model=schemas.EdgeTypeRead)
def create_edge_type(edge_type: schemas.EdgeTypeCreate, session: Session = Depends(get_session)):
    db_edge_type = EdgeType.model_validate(edge_type)
    session.add(db_edge_type)
    session.commit()
    session.refresh(db_edge_type)
    return db_edge_type
