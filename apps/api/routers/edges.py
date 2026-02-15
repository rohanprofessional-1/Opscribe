from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Edge, EdgeType
from apps.api import schemas

router = APIRouter(
    prefix="/edges",
    tags=["edges"]
)

@router.post("/", response_model=schemas.EdgeRead)
def create_edge(edge: schemas.EdgeCreate, session: Session = Depends(get_session)):
    # Verify EdgeType exists
    edge_type = session.get(EdgeType, edge.edge_type_id)
    if not edge_type:
        raise HTTPException(status_code=404, detail="EdgeType not found")

    db_edge = Edge.model_validate(edge)
    session.add(db_edge)
    session.commit()
    session.refresh(db_edge)
    return db_edge

@router.get("/{edge_id}", response_model=schemas.EdgeRead)
def read_edge(edge_id: UUID, session: Session = Depends(get_session)):
    edge = session.get(Edge, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    return edge

@router.delete("/{edge_id}")
def delete_edge(edge_id: UUID, session: Session = Depends(get_session)):
    edge = session.get(Edge, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    session.delete(edge)
    session.commit()
    return {"ok": True}
