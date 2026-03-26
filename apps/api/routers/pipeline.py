"""
Pipeline Router — Triggers per-tenant data export to S3.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from apps.api.database import get_session
from apps.api.models import Client, ConnectedRepository, ClientIntegration, Graph
from apps.api.utils.encryption import decrypt_dict

import logging
import asyncio
from collections import defaultdict
from apps.api.ingestors.pipeline.ingestors import AWSIngestor, GitHubIngestor, GitHubLinkIngestor
from apps.api.ingestors.pipeline.s3_exporter import S3Exporter
from apps.api.ingestors.pipeline.db_exporter import DbExporter
from apps.api.ingestors.pipeline.base import BaseIngestor, BaseExporter

logger = logging.getLogger(__name__)

# Concurrency & Caching Guards
REPO_LOCKS = defaultdict(asyncio.Lock)
INGESTION_CACHE = {} # maps repo_url:branch -> last_successful_commit_sha

router = APIRouter(
    prefix="/pipeline",
    tags=["pipeline"],
)

class ExportRequest(BaseModel):
    client_id: str
    include_aws: bool = True
    include_github: bool = True
    aws_region: str = "us-east-1"

class GithubLinkRequest(BaseModel):
    client_id: str
    repo_url: str = Field(..., description="The GitHub repository URL")
    branch: Optional[str] = "main"
    auth_token: Optional[str] = None

    @field_validator("repo_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith("https://github.com/"):
            raise ValueError("Only https://github.com/ URLs are supported.")
        # Attempt to extract org/repo
        parts = v.split("github.com/")[-1].split("/")
        if len(parts) < 2:
            raise ValueError("Invalid repository URL format.")
        org, repo = parts[0], parts[1].replace(".git", "")
        return f"https://github.com/{org}/{repo}"

class ExportResponse(BaseModel):
    status: str
    message: str

async def run_export(
    client_id: str,
    ingestors: List[BaseIngestor],
    exporter: BaseExporter,
):
    try:
        results = []
        for ingestor in ingestors:
            ingestor_results = await ingestor.ingest()
            if ingestor_results:
                results.extend(ingestor_results)
        
        if results:
            await DbExporter().export(client_id=client_id, results=results, label="export")
            await S3Exporter().export(client_id=client_id, results=results, label="export")
    except Exception as e:
        logger.error(f"Pipeline export failed: {e}")

@router.post("/export", response_model=ExportResponse)
async def trigger_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Trigger a background export of combined AWS + GitHub data to S3."""
    # Verify client exists
    client = session.get(Client, request.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Fetch active client integrations
    aws_integration = session.exec(
        select(ClientIntegration).where(
            ClientIntegration.client_id == request.client_id,
            ClientIntegration.provider == "aws",
            ClientIntegration.is_active == True
        )
    ).first()

    # Import the source of truth for encrypted keys
    from apps.api.routers.integrations import SENSITIVE_KEYS

    ingestors: List[BaseIngestor] = []
    if request.include_aws:
        aws_creds = decrypt_dict(aws_integration.credentials, SENSITIVE_KEYS) if aws_integration else {}
        ingestors.append(AWSIngestor(region_name=request.aws_region, credentials=aws_creds))
    
    if request.include_github:
        ingestors.append(GitHubIngestor(client_id=request.client_id, session=session))

    background_tasks.add_task(
        run_export,
        client_id=request.client_id,
        ingestors=ingestors,
        exporter=DbExporter(),
    )

    return ExportResponse(
        status="started",
        message=f"Export pipeline started for client {request.client_id}. Data will be exported to S3.",
    )


async def run_github_link(
    client_id: str,
    ingestor: BaseIngestor,
    exporter: BaseExporter,
    repo_url: str,
):
    branch = getattr(ingestor.pipeline, "branch", "main")
    lock_key = f"{client_id}:{repo_url}:{branch}"
    
    async with REPO_LOCKS[lock_key]:
        try:
            commit_sha = await ingestor.pipeline.get_remote_sha()
            if commit_sha and INGESTION_CACHE.get(lock_key) == commit_sha:
                logger.info(f"Skipping ingestion for {lock_key}, cache hit for commit {commit_sha}")
                return

            results = await ingestor.ingest()
            label = f"github_link_export_{repo_url.split('/')[-1] if '/' in repo_url else 'repo'}"
            if results:
                await DbExporter().export(client_id=client_id, results=results, label=label)
                await S3Exporter().export(client_id=client_id, results=results, label=label)
                if commit_sha:
                    INGESTION_CACHE[lock_key] = commit_sha

        except Exception as e:
            logger.error(f"GitHub link ingestion failed for {repo_url}: {e}")


@router.post("/github-link", response_model=ExportResponse)
async def trigger_github_link(
    request: GithubLinkRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Trigger a background ingestion of a public GitHub URL directly to S3."""
    client = session.get(Client, request.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Rate Limiting: Max 5 ingestions per user per hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    # Using python filtering since naive datetimes might complain, but SQLModel can do this
    recent_graphs = session.exec(
        select(Graph).where(Graph.client_id == client.id)
    ).all()
    recent_count = sum(1 for g in recent_graphs if g.created_at and g.created_at >= one_hour_ago.replace(tzinfo=None))
    
    if recent_count >= 5:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 5 ingestions per hour.")

    # Instantiate the ingestor, passing the access token if provided
    ingestor = GitHubLinkIngestor(
        repo_url=request.repo_url, 
        branch=request.branch, 
        access_token=request.auth_token
    )
    exporter = DbExporter()

    background_tasks.add_task(
        run_github_link,
        client_id=request.client_id,
        ingestor=ingestor,
        exporter=exporter,
        repo_url=request.repo_url,
    )

    return ExportResponse(
        status="started",
        message=f"GitHub link ingestion started for client {request.client_id}. Data will be exported directly to Postgres.",
    )
