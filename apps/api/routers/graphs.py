from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Graph, Node, Edge, NodeType, EdgeType
from apps.api import schemas

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

@router.delete("/{graph_id}")
def delete_graph(graph_id: UUID, session: Session = Depends(get_session)):
    graph = session.get(Graph, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
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
