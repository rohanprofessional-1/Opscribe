from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select
from typing import List
from uuid import UUID, uuid4

from apps.api.database import get_session
from apps.api.models import Client, Graph
from apps.api import schemas

from apps.api.utils.auth import get_current_client_id

# The hardcoded DEV_USER_ID has been removed. All users must authenticate via Auth0.

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/me", response_model=schemas.ClientRead)
def get_current_user(
    client_id: UUID = Depends(get_current_client_id), 
    session: Session = Depends(get_session)
):
    """
    Returns the currently authenticated Opscribe Client.
    Validates the Auth0 JWT and queries the database via the mapped ID.
    """
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found in database")
    
    return client


@router.post("/", response_model=schemas.ClientRead)
def create_client(client: schemas.ClientCreate, session: Session = Depends(get_session)):
    db_client = Client.model_validate(client)
    session.add(db_client)
    session.commit()
    session.refresh(db_client)
    return db_client

@router.get("/{client_id}", response_model=schemas.ClientRead)
def read_client(client_id: UUID, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/{client_id}/graphs", response_model=List[schemas.GraphRead])
def list_client_graphs(client_id: UUID, session: Session = Depends(get_session)):
    """List all infrastructure designs (graphs) for a client. Use this for the dashboard."""
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    graphs = session.exec(select(Graph).where(Graph.client_id == client_id).order_by(Graph.updated_at.desc())).all()
    return graphs
