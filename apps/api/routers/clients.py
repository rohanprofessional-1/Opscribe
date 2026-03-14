from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select
from typing import List
from uuid import UUID, uuid4

from apps.api.database import get_session
from apps.api.models import Client, Graph
from apps.api import schemas

# Hardcoded dev user ID until Auth0 is fully integrated
DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/me", response_model=schemas.ClientRead)
def get_current_user(session: Session = Depends(get_session)):
    """
    Temporary placeholder for a JWT-based /me endpoint. 
    Returns a consistent 'Dev User' client until auth is fully implemented.
    """
    client = session.get(Client, DEV_USER_ID)
    if not client:
        client = Client(
            id=DEV_USER_ID,
            name="Dev User",
            metadata_={"role": "admin", "temporary_auth": True},
        )
        session.add(client)
        session.commit()
        session.refresh(client)
    
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
