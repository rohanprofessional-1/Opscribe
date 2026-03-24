from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
import os

from apps.api.database import get_session
from apps.api.models import Client, ConnectedRepository, PlatformConfig
from apps.api.ingestors.pipeline.s3_exporter import S3Exporter
from apps.api.ingestors.pipeline.ingestors import GitHubIngestor
from apps.api.routers.pipeline import run_export
from apps.api.routers.clients import DEV_USER_ID
from apps.api.utils.encryption import encrypt_value, decrypt_value

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# ─────────────────────────────────────────────────────────────────────────────
# GitHub App Platform Configuration
# ─────────────────────────────────────────────────────────────────────────────

SENSITIVE_CONFIG_KEYS = {"github_app_private_key"}

class GitHubAppConfig(BaseModel):
    app_id: str
    private_key: str   # PEM string — will be encrypted before storage
    app_slug: str      # e.g. "opscribe-app" — used to build the install URL

class GitHubAppConfigResponse(BaseModel):
    app_id: Optional[str] = None
    app_slug: Optional[str] = None
    private_key_configured: bool = False

def _upsert_config(key: str, value: str, session: Session, sensitive: bool = False):
    """Upsert a single PlatformConfig row, encrypting the value if sensitive."""
    stored_value = encrypt_value(value) if sensitive else value
    existing = session.get(PlatformConfig, key)
    if existing:
        existing.value = stored_value
        session.add(existing)
    else:
        session.add(PlatformConfig(key=key, value=stored_value))

def _get_config(key: str, session: Session, sensitive: bool = False) -> Optional[str]:
    """Read a single PlatformConfig row, decrypting if sensitive."""
    row = session.get(PlatformConfig, key)
    if not row:
        return None
    return decrypt_value(row.value) if sensitive else row.value

@router.post("/github-app")
def configure_github_app(config: GitHubAppConfig, session: Session = Depends(get_session)):
    """
    Save (or update) the GitHub App credentials into the platform_config table.
    The private key is encrypted using OPSCRIBE_MASTER_KEY before storage.
    """
    _upsert_config("github_app_id", config.app_id, session)
    _upsert_config("github_app_private_key", config.private_key, session, sensitive=True)
    _upsert_config("github_app_slug", config.app_slug, session)
    session.commit()
    return {"status": "success", "message": "GitHub App credentials saved to database."}

@router.get("/github-app", response_model=GitHubAppConfigResponse)
def get_github_app_config(session: Session = Depends(get_session)):
    """Return the stored GitHub App config, masking the private key."""
    return GitHubAppConfigResponse(
        app_id=_get_config("github_app_id", session),
        app_slug=_get_config("github_app_slug", session),
        private_key_configured=bool(_get_config("github_app_private_key", session, sensitive=True)),
    )

def bootstrap_github_app_from_env(session: Session):
    """
    One-time bootstrap: if GITHUB_APP_ID is set in the environment but NOT yet in the
    database, seed the platform_config table automatically. After this runs once the
    env vars can be removed.
    """
    existing_id = session.get(PlatformConfig, "github_app_id")
    if existing_id:
        return  # Already configured in DB — nothing to do

    app_id = os.environ.get("GITHUB_APP_ID")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
    app_slug = os.environ.get("GITHUB_APP_SLUG", "")

    if app_id and private_key:
        private_key = private_key.replace("\\n", "\n")
        _upsert_config("github_app_id", app_id, session)
        _upsert_config("github_app_private_key", private_key, session, sensitive=True)
        if app_slug:
            _upsert_config("github_app_slug", app_slug, session)
        session.commit()
        print("✅ Bootstrap: GitHub App credentials seeded from environment into platform_config.")
    else:
        print("⚠️  Bootstrap: GITHUB_APP_ID/GITHUB_APP_PRIVATE_KEY not found. Configure via POST /admin/github-app.")


# ─────────────────────────────────────────────────────────────────────────────
# Scaffold (legacy dev helper)
# ─────────────────────────────────────────────────────────────────────────────

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
    Dev shortcut: saves a GitHub App installation ID directly into the dev client,
    creates the repository record, and kicks off an immediate S3 ingestion.
    """
    client = session.get(Client, DEV_USER_ID)
    if not client:
        client = Client(
            id=DEV_USER_ID,
            name="Opscribe Org",
            metadata_={"role": "admin", "temporary_auth": True},
        )
        session.add(client)
        session.commit()

    client.metadata_ = dict(client.metadata_ or {})
    client.metadata_["github_installation_id"] = request.installation_id
    session.add(client)
    session.commit()

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
        "message": "Organization scaffolded and ingestion pipeline started.",
        "organization_id": DEV_USER_ID,
        "repository_id": repo.id
    }

