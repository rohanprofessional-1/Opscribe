from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
import httpx
import os
import json
from uuid import UUID

from apps.api.database import get_session
from apps.api.models import Client, ConnectedRepository
from apps.api.infrastructure.github.security import encrypt_token, decrypt_token
from apps.api.infrastructure.github.client import GitHubClient
from apps.api.infrastructure.repo.walker import RepositoryWalker

router = APIRouter(
    prefix="/github",
    tags=["github"]
)

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "mock_client_id")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "mock_client_secret")
GITHUB_REDIRECT_URI = os.environ.get("GITHUB_REDIRECT_URI", "http://localhost:8000/github/callback")
WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "mock_webhook_secret")

@router.get("/login")
def github_login(client_id: UUID = Query(..., description="The opscribe Client/Tenant ID")):
    """Redirects the user to the GitHub OAuth authorization page."""
    state = str(client_id)
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=repo,metadata:read"
        f"&state={state}"
    )
    return RedirectResponse(url)

@router.get("/callback")
async def github_callback(code: str, state: str, session: Session = Depends(get_session)):
    """Handles the OAuth callback, exchanges code for token, and stores it in Client metadata."""
    try:
        client_uuid = UUID(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    db_client = session.get(Client, client_uuid)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"}
        )
        data = response.json()
        
        if "error" in data:
            raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {data['error_description']}")
            
        access_token = data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token")

    db_client.metadata_ = dict(db_client.metadata_ or {})
    db_client.metadata_["temp_github_token"] = encrypt_token(access_token)
    session.add(db_client)
    session.commit()

    return RedirectResponse(url="http://localhost:5173/?github_connected=true")

@router.get("/repos")
async def get_repositories(client_id: UUID, session: Session = Depends(get_session)):
    """Fetches the authenticated user's repositories."""
    db_client = session.get(Client, client_id)
    if not db_client or not db_client.metadata_ or "temp_github_token" not in db_client.metadata_:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    plain_token = decrypt_token(db_client.metadata_["temp_github_token"])
    gh_client = GitHubClient(access_token=plain_token)
    
    try:
        repos = await gh_client.get_user_repositories()
        return [
            {"name": r["full_name"], "default_branch": r["default_branch"]}
            for r in repos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")

from pydantic import BaseModel

class ConnectRepoRequest(BaseModel):
    client_id: UUID
    repo_url: str
    default_branch: str

@router.post("/connect")
async def connect_repository(request: ConnectRepoRequest, session: Session = Depends(get_session)):
    """Saves the selected repository and registers a webhook."""
    db_client = session.get(Client, request.client_id)
    if not db_client or not db_client.metadata_ or "temp_github_token" not in db_client.metadata_:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    encrypted_token = db_client.metadata_["temp_github_token"]
    plain_token = decrypt_token(encrypted_token)
    
    repo = ConnectedRepository(
        client_id=request.client_id,
        repo_url=request.repo_url,
        default_branch=request.default_branch,
        encrypted_access_token=encrypted_token,
        ingestion_status="pending"
    )
    session.add(repo)
    session.commit()
    session.refresh(repo)

    gh_client = GitHubClient(access_token=plain_token)
    try:
        parts = request.repo_url.replace("https://github.com/", "").split("/")
        owner, repo_name = parts[0], parts[1]
        webhook_target = os.environ.get("PUBLIC_API_URL", "https://your-domain.ngrok-free.app") + "/github/webhook"
        
        await gh_client.create_webhook(owner, repo_name, webhook_target, WEBHOOK_SECRET)
    except Exception as e:
        print(f"Warning: Failed to set webhook on {request.repo_url}: {str(e)}")

    return {"status": "success", "repository_id": repo.id}


async def process_repository_ingestion(repo_url: str, branch: str, encrypted_token: str):
    """Background task to clone and walk the repository."""
    print(f"Starting ingestion process for {repo_url} on branch {branch}...")
    try:
        plain_token = decrypt_token(encrypted_token)
        walker = RepositoryWalker(repo_url=repo_url, branch=branch, access_token=plain_token)
        file_set = await walker.clone_and_walk()
        
        print(f"[{repo_url}] Walk successful.")
        print(f"   => Found {len(file_set.tier_1_files)} Tier 1 files.")
        print(f"   => Found {len(file_set.tier_2_files)} Tier 2 files.")
        # Future: Pass this file_set to the parsers down the pipeline
        
    except Exception as e:
        print(f"[{repo_url}] Background ingestion failed: {str(e)}")


@router.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """Receives GitHub push events to trigger re-ingestion."""
    
    event = request.headers.get("X-GitHub-Event")
    if event != "push":
        return {"status": "ignored", "reason": "not a push event"}

    payload = await request.json()
    repo_url = payload.get("repository", {}).get("html_url")
    ref = payload.get("ref", "")
    
    if not repo_url:
        return {"status": "ignored", "reason": "no repository url"}

    stmt = select(ConnectedRepository).where(ConnectedRepository.repo_url == repo_url)
    connected_repos = session.exec(stmt).all()

    for connected in connected_repos:
        if ref == f"refs/heads/{connected.default_branch}":
            connected.ingestion_status = "pending"
            session.add(connected)
            print(f"Scheduling background ingestion for {connected.repo_url}")
            background_tasks.add_task(
                process_repository_ingestion, 
                repo_url=connected.repo_url, 
                branch=connected.default_branch, 
                encrypted_token=connected.encrypted_access_token
            )

    session.commit()
    return {"status": "success", "message": "Webhook processed"}
