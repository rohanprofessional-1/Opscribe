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
from apps.api.ingestors.github.incremental import IncrementalUpdater
from apps.api.routers.pipeline import run_export
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/github",
    tags=["github"]
)

@router.get("/config")
def github_config(client_id: UUID, session: Session = Depends(get_session)):
    """Returns the custom GitHub App configuration needed by the frontend for this specific client."""
    from apps.api.models import ClientIntegration
    from apps.api.utils.encryption import decrypt_dict
    from apps.api.routers.integrations import SENSITIVE_KEYS

    statement = select(ClientIntegration).where(
        ClientIntegration.client_id == client_id,
        ClientIntegration.provider == "github_app",
        ClientIntegration.is_active == True
    )
    integration = session.exec(statement).first()
    
    if not integration:
        return {"configured": False, "app_install_url": None}

    creds = decrypt_dict(integration.credentials, SENSITIVE_KEYS)
    slug = (creds.get("github_app_slug") or "").strip()
    
    if not slug:
        return {"configured": False, "app_install_url": None}
        
    return {
        "configured": True,
        "app_install_url": f"https://github.com/apps/{slug}/installations/new",
    }

@router.get("/app/callback")
async def github_app_callback(
    installation_id: str, 
    setup_action: str = None, 
    state: str = None, 
    client_id: str = None,
    session: Session = Depends(get_session)
):
    """
    Handles the redirect after a user installs the GitHub App on their organization/account.
    The 'state' or 'client_id' parameter MUST contain the Opscribe `client_id` to link the installation.
    """
    effective_client_id = state or client_id
    if effective_client_id:
        try:
            client_uuid = UUID(effective_client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid client ID parameter format")
    else:
        raise HTTPException(
            status_code=400, 
            detail="Missing client_id or state parameter. Opscribe GitHub App must be installed via the dashboard Setup URL."
        )

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
    print(f"DEBUG: Fetching repos for client {client_id} with installation {installation_id}")

    try:
        # Session passed through so app_auth reads credentials from DB
        token = await get_installation_token(installation_id, str(client_id), session)
        print(f"DEBUG: Generated installation token: {token[:5]}...")
        gh_client = GitHubClient(access_token=token)

        all_repos = []
        page = 1
        
        while True:
            response = await gh_client._request_with_retry("GET", f"/installation/repositories?per_page=100&page={page}")
            data = response.json()
            page_repos = data.get("repositories", [])
            
            if not page_repos:
                break
                
            all_repos.extend(page_repos)
            
            if len(page_repos) < 100:
                break
                
            page += 1
            
        # Fetch existing connected repositories to mark the live list
        stmt = select(ConnectedRepository).where(ConnectedRepository.client_id == client_id)
        connected_list = session.exec(stmt).all()
        connected_map = {r.repo_url: r for r in connected_list}
        
        print(f"DEBUG: Found {len(all_repos)} repositories total across {page} pages. {len(connected_list)} are already connected.")

        return [
            {
                "id": str(r["id"]), 
                "name": r["full_name"], 
                "default_branch": r["default_branch"],
                "is_connected": f"https://github.com/{r['full_name']}" in connected_map,
                "last_ingested_at": getattr(connected_map.get(f"https://github.com/{r['full_name']}"), "last_ingested_at", None),
                "ingestion_status": getattr(connected_map.get(f"https://github.com/{r['full_name']}"), "ingestion_status", None)
            }
            for r in all_repos
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

    session.add(repo)
    session.commit()
    session.refresh(repo)

    return {"status": "success", "repository_id": repo.id}


@router.post("/webhook")
async def github_webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    session: Session = Depends(get_session),
    client_id: str = Query(...)
):
    """Receives GitHub App events to trigger re-ingestion for the querying client."""
    from apps.api.models import ClientIntegration
    from apps.api.utils.encryption import decrypt_dict
    from apps.api.routers.integrations import SENSITIVE_KEYS
    import hmac
    import hashlib

    # 1. (Optional) Signature Verification — if client has a Webhook Secret configured
    statement = select(ClientIntegration).where(
        ClientIntegration.client_id == client_id,
        ClientIntegration.provider == "github_app"
    )
    integration = session.exec(statement).first()
    
    if integration:
        creds = decrypt_dict(integration.credentials, SENSITIVE_KEYS)
        secret = creds.get("github_webhook_secret")
        
        if secret:
            signature = request.headers.get("X-Hub-Signature-256")
            if not signature:
                raise HTTPException(status_code=401, detail="Webhook signature missing")
            
            body = await request.body()
            expected_signature = "sha256=" + hmac.new(
                secret.encode("utf-8"),
                msg=body,
                digestmod=hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                raise HTTPException(status_code=401, detail="Webhook signature invalid")

    # 2. Process Payload
    event = request.headers.get("X-GitHub-Event")
    if event not in ("push", "pull_request"):
        return {"status": "ignored", "reason": f"unhandled event type: {event}"}

    payload = await request.json()
    repo_url = payload.get("repository", {}).get("html_url")

    installation_id = str(payload.get("installation", {}).get("id", ""))

    if not repo_url or not installation_id:
        return {"status": "ignored", "reason": "missing repo or installation id"}

    stmt = select(ConnectedRepository).where(
        ConnectedRepository.repo_url == repo_url,
        ConnectedRepository.installation_id == installation_id,
        ConnectedRepository.client_id == client_id
    )
    connected_repos = session.exec(stmt).all()

    for connected in connected_repos:
        # Check if this app installation matches our records
        if event == "push":
            ref = payload.get("ref", "")
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
        elif event == "pull_request":
            action = payload.get("action")
            if action in ("opened", "synchronize", "reopened"):
                pull_number = payload.get("pull_request", {}).get("number")
                branch_ref = payload.get("pull_request", {}).get("head", {}).get("ref")
                
                logger.info(f"Scheduling background incremental update for PR #{pull_number}")
                updater = IncrementalUpdater(
                    session=session,
                    tenant_id=str(connected.client_id),
                    repo_url=repo_url,
                    installation_id=installation_id
                )

                background_tasks.add_task(
                    updater.update_from_pr,
                    pull_number=pull_number,
                    branch_ref=branch_ref
                )

    session.commit()
    return {"status": "success", "message": f"App Webhook processed for event: {event}"}


@router.get("/datalake")
async def get_datalake_preview(client_id: UUID):
    """
    Returns a preview of the MinIO data lake for a given client, including:
    - The file tree of all stored objects
    - The latest.json payload (if it exists)
    """
    try:
        exporter = S3Exporter()
        s3 = exporter.s3
        bucket = exporter.bucket
        prefix = f"{client_id}/"

        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        files = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            files.append({
                "key": key,
                "size_bytes": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            })

        # Try to read the latest.json
        latest_payload = None
        latest_key = f"{client_id}/github/latest.json"
        try:
            body = s3.get_object(Bucket=bucket, Key=latest_key)["Body"].read().decode()
            latest_payload = json.loads(body)
        except Exception:
            pass  # No latest.json yet

        return {
            "bucket": bucket,
            "client_id": str(client_id),
            "file_count": len(files),
            "files": files,
            "latest_payload": latest_payload,
        }
    except Exception as e:
        logger.error(f"Failed to read data lake for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read data lake: {str(e)}")

