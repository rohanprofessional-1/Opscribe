from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Client, Graph
from apps.api import schemas, auth

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.post("/", response_model=schemas.ClientRead)
def create_client(client: schemas.ClientCreate, session: Session = Depends(get_session)):
    db_client = Client.model_validate(client)
    session.add(db_client)
    session.commit()
    session.refresh(db_client)
    return db_client

@router.get("/{client_id}", response_model=schemas.ClientRead)
def read_client(
    client_id: UUID,
    session: Session = Depends(get_session),
    current_client: Client = Depends(auth.get_current_client)
):
    if str(current_client.id) != str(client_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_client

@router.get("/{client_id}/graphs", response_model=List[schemas.GraphRead])
def list_client_graphs(
    client_id: UUID, 
    session: Session = Depends(get_session),
    current_client: Client = Depends(auth.get_current_client)
):
    """List all infrastructure designs (graphs) for a client."""
    if str(current_client.id) != str(client_id):
        raise HTTPException(status_code=403, detail="Not authorized to access items for this client")
        
    graphs = session.exec(select(Graph).where(Graph.client_id == client_id).order_by(Graph.updated_at.desc())).all()
    return graphs
