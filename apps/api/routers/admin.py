from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Client, ConnectedRepository
from apps.api.ingestors.pipeline.s3_exporter import S3Exporter
from apps.api.ingestors.pipeline.ingestors import GitHubIngestor
from apps.api.routers.pipeline import run_export
from apps.api.routers.clients import DEV_USER_ID

import os

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

class ScaffoldOrgRequest(BaseModel):
    installation_id: str
    target_repo_id: str
    target_repo_url: str
    default_branch: str = "main"

@router.post("/scaffold-org")
async def scaffold_organization(
    request: ScaffoldOrgRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Mock enterprise setup: 
    Saves a GitHub App installation ID directly into the Client/Organization holding the dev user, 
    creates the repository record, and kicks off an immediate S3 ingestion in the background.
    """
    
    # 1. Ensure the Organization (Client) exists (using DEV_USER_ID for now)
    client = session.get(Client, DEV_USER_ID)
    if not client:
        client = Client(
            id=DEV_USER_ID,
            name="Opscribe Org",
            metadata_={"role": "admin", "temporary_auth": True},
        )
        session.add(client)
        session.commit()
    
    # 2. Save the Installation ID to bypass the GitHub App UI flow
    client.metadata_ = dict(client.metadata_ or {})
    client.metadata_["github_installation_id"] = request.installation_id
    session.add(client)
    session.commit()

    # 3. Create the ConnectedRepository Record
    repo = session.exec(
        select(ConnectedRepository)
        .where(ConnectedRepository.client_id == DEV_USER_ID)
        .where(ConnectedRepository.repo_url == request.target_repo_url)
    ).first()

    if not repo:
        repo = ConnectedRepository(
            client_id=DEV_USER_ID,
            repo_url=request.target_repo_url,
            default_branch=request.default_branch,
            installation_id=request.installation_id,
            target_repo_id=request.target_repo_id,
            ingestion_status="pending"
        )
        session.add(repo)
        session.commit()
        session.refresh(repo)

    # 4. Kick off immediate ingestion (App Webhooks are handled by GitHub automatically)
    ingestor = GitHubIngestor(client_id=str(DEV_USER_ID), session=session, repo_url=request.target_repo_url)
    exporter = S3Exporter()
    background_tasks.add_task(
        run_export,
        client_id=str(DEV_USER_ID),
        ingestors=[ingestor],
        exporter=exporter
    )
    
    return {
        "status": "success",
        "message": "Organization scaffolded and ingestion pipeline started using GitHub App Integration.",
        "organization_id": DEV_USER_ID,
        "repository_id": repo.id
    }
