from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select
from typing import List
from uuid import UUID, uuid4

from apps.api.database import get_session
from apps.api.models import Client, Graph
from apps.api import schemas

# Cookie and header used by nginx + frontend for anonymous client identity
ANON_COOKIE_NAME = "anonymous_client_id"
ANON_HEADER_NAME = "X-Client-ID"
ANON_COOKIE_MAX_AGE = 365 * 24 * 3600  # 1 year

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/anon/session", response_model=schemas.ClientRead)
def get_or_create_anonymous_client(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    Get-or-create an anonymous client for the current visitor.
    Prefer X-Client-ID (set by nginx from cookie). Else read cookie.
    If none or invalid, create a new Client and set cookie so nginx can 
    pass it next time.
    """
    client_id_raw = request.headers.get(ANON_HEADER_NAME) or request.cookies.get(ANON_COOKIE_NAME)
    if client_id_raw:
        try:
            client_id = UUID(client_id_raw)
            client = session.get(Client, client_id)
            if client:
                return client
        except (ValueError, TypeError):
            pass
    # Create new anonymous client
    new_id = uuid4()
    client = Client(
        id=new_id,
        name="Anonymous",
        metadata_={"anonymous": True},
    )
    session.add(client)
    session.commit()
    session.refresh(client)
    response.set_cookie(
        key=ANON_COOKIE_NAME,
        value=str(new_id),
        max_age=ANON_COOKIE_MAX_AGE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
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
