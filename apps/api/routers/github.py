from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
import httpx
import os
import json
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Client, ConnectedRepository, PlatformConfig
from apps.api.ingestors.github.app_auth import get_installation_token
from apps.api.ingestors.github.client import GitHubClient
from apps.api.ingestors.pipeline.s3_exporter import S3Exporter
from apps.api.ingestors.pipeline.ingestors import GitHubIngestor
from apps.api.routers.pipeline import run_export
from apps.api.routers.clients import DEV_USER_ID

router = APIRouter(
    prefix="/github",
    tags=["github"]
)

@router.get("/config")
def github_config(session: Session = Depends(get_session)):
    """Returns public GitHub App configuration needed by the frontend."""
    slug_row = session.get(PlatformConfig, "github_app_slug")
    if not slug_row or not slug_row.value:
        raise HTTPException(
            status_code=500,
            detail="GitHub App not configured. POST /admin/github-app to set credentials."
        )
    return {
        "app_install_url": f"https://github.com/apps/{slug_row.value}/installations/new",
    }

@router.get("/app/callback")
async def github_app_callback(installation_id: str, setup_action: str = None, state: str = None, session: Session = Depends(get_session)):
    """
    Handles the redirect after a user installs the GitHub App on their organization/account.
    The 'state' parameter should contain the Opscribe client_id.
    Falls back to the DEV_USER_ID if no state is provided (dev mode).
    """
    if state:
        try:
            client_uuid = UUID(state)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid state parameter format")
    else:
        # Dev mode: use the default dev client
        client_uuid = DEV_USER_ID

    db_client = session.get(Client, client_uuid)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Save the installation ID to the client metadata
    db_client.metadata_ = dict(db_client.metadata_ or {})
    db_client.metadata_["github_installation_id"] = installation_id
    session.add(db_client)
    session.commit()

    return RedirectResponse(url="http://localhost:5173/?github_app_installed=true")

@router.get("/repos")
async def get_repositories(client_id: UUID, session: Session = Depends(get_session)):
    """Fetches the repositories available to this GitHub App Installation."""
    db_client = session.get(Client, client_id)
    if not db_client or not db_client.metadata_ or "github_installation_id" not in db_client.metadata_:
        raise HTTPException(status_code=401, detail="GitHub App not installed for this client")

    installation_id = db_client.metadata_["github_installation_id"]

    try:
        # Session passed through so app_auth reads credentials from DB
        token = await get_installation_token(installation_id, session)
        gh_client = GitHubClient(access_token=token)

        response = await gh_client._request_with_retry("GET", "/installation/repositories")
        repos = response.json().get("repositories", [])

        return [
            {"id": str(r["id"]), "name": r["full_name"], "default_branch": r["default_branch"]}
            for r in repos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")

@router.get("/connected-repos")
async def get_connected_repos(client_id: UUID, session: Session = Depends(get_session)):
    """Fetches the opscribe ConnectedRepository records to check ingestion status."""
    statement = select(ConnectedRepository).where(ConnectedRepository.client_id == client_id)
    repos = session.exec(statement).all()
    return repos

from pydantic import BaseModel

class ConnectRepoRequest(BaseModel):
    client_id: UUID
    repo_url: str
    target_repo_id: str
    default_branch: str

@router.post("/connect")
async def connect_repository(
    request: ConnectRepoRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Saves the selected repository to the database and schedules an initial baseline ingestion.
    """
    db_client = session.get(Client, request.client_id)
    if not db_client or not db_client.metadata_ or "github_installation_id" not in db_client.metadata_:
        raise HTTPException(status_code=401, detail="GitHub App not installed")

    installation_id = db_client.metadata_["github_installation_id"]

    repo = ConnectedRepository(
        client_id=request.client_id,
        repo_url=request.repo_url,
        default_branch=request.default_branch,
        installation_id=str(installation_id),
        target_repo_id=request.target_repo_id,
        ingestion_status="pending"
    )
    session.add(repo)
    session.commit()
    session.refresh(repo)

    ingestor = GitHubIngestor(client_id=str(request.client_id), session=session, repo_url=request.repo_url)
    exporter = S3Exporter()
    background_tasks.add_task(
        run_export,
        client_id=str(request.client_id),
        ingestors=[ingestor],
        exporter=exporter
    )

    return {"status": "success", "repository_id": repo.id}


@router.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """Receives GitHub App events to trigger re-ingestion."""

    event = request.headers.get("X-GitHub-Event")
    if event != "push":
        return {"status": "ignored", "reason": "not a push event"}

    payload = await request.json()
    repo_url = payload.get("repository", {}).get("html_url")
    ref = payload.get("ref", "")

    installation_id = str(payload.get("installation", {}).get("id", ""))

    if not repo_url or not installation_id:
        return {"status": "ignored", "reason": "missing repo or installation id"}

    stmt = select(ConnectedRepository).where(
        ConnectedRepository.repo_url == repo_url,
        ConnectedRepository.installation_id == installation_id
    )
    connected_repos = session.exec(stmt).all()

    for connected in connected_repos:
        if ref == f"refs/heads/{connected.default_branch}":
            connected.ingestion_status = "pending"
            session.add(connected)

            print(f"Scheduling background App ingestion for {connected.repo_url}")
            ingestor = GitHubIngestor(client_id=str(connected.client_id), session=session, repo_url=connected.repo_url)
            exporter = S3Exporter()
            background_tasks.add_task(
                run_export,
                client_id=str(connected.client_id),
                ingestors=[ingestor],
                exporter=exporter
            )

    session.commit()
    return {"status": "success", "message": "App Webhook processed"}


