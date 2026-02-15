from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Dict, Any
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Node, NodeType
from apps.api import schemas

router = APIRouter(
    prefix="/nodes",
    tags=["nodes"]
)

def validate_node_properties(node_type: NodeType, properties: Dict[str, Any]):
    """
    Validates that the provided properties match the allowed properties in the NodeType.
    If allowed_properties is empty, we assume no restriction (or strict restriction? Default to strict based on request).
    The request says: "return error if some information is not present".
    Implying: allowed_properties defines REQUIRED properties.
    """
    allowed = set(node_type.allowed_properties) if node_type.allowed_properties else set()
    provided = set(properties.keys())
    
    # Check for missing required properties
    missing = allowed - provided
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required properties for node type '{node_type.name}': {', '.join(missing)}"
        )
    
    # Optionally check for extra properties? The prompt focuses on "not present", so missing is key.
    # We can allow extra properties or not. Let's allow flexibility for now unless strict schema is needed.

@router.post("/", response_model=schemas.NodeRead)
def create_node(node: schemas.NodeCreate, session: Session = Depends(get_session)):
    # 1. Fetch NodeType to validate properties
    node_type = session.get(NodeType, node.node_type_id)
    if not node_type:
        raise HTTPException(status_code=404, detail="NodeType not found")
    
    # 2. Validate Properties
    validate_node_properties(node_type, node.properties)
    
    # 3. Create Node
    db_node = Node.model_validate(node)
    session.add(db_node)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        # Handle unique constraint violation (client_id, graph_id, key)
        if "unique_node_client_graph_key" in str(e):
            raise HTTPException(status_code=409, detail="Node with this key already exists in the graph.")
        raise e
        
    session.refresh(db_node)
    return db_node

@router.get("/{node_id}", response_model=schemas.NodeRead)
def read_node(node_id: UUID, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node

@router.delete("/{node_id}")
def delete_node(node_id: UUID, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    session.delete(node)
    session.commit()
    return {"ok": True}
