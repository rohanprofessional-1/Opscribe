"""
Pipeline Router — Triggers per-tenant data export to S3.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional, List

from apps.api.database import get_session
from apps.api.models import Client, ConnectedRepository
from apps.api.ingestors.aws.schemas import DiscoveryResult
from apps.api.ingestors.pipeline.s3_exporter import S3Exporter
from apps.api.ingestors.pipeline.base import BaseIngestor, BaseExporter
from apps.api.ingestors.pipeline.ingestors import AWSIngestor, GitHubIngestor, GitHubLinkIngestor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pipeline",
    tags=["Pipeline"],
)


class ExportRequest(BaseModel):
    client_id: str
    include_aws: bool = True
    include_github: bool = True
    aws_region: str = "us-east-1"


class GithubLinkRequest(BaseModel):
    repo_url: str
    client_id: str
    branch: str = "main"


class ExportResponse(BaseModel):
    status: str
    message: str


async def run_export(
    client_id: str,
    ingestors: List[BaseIngestor],
    exporter: BaseExporter,
):
    """Background task to run full export pipeline."""
    results: List[DiscoveryResult] = []

    print(f"DEBUG: Starting run_export for client {client_id}")
    for ingestor in ingestors:
        try:
            print(f"DEBUG: Running ingestor {ingestor.source_name}...")
            res = await ingestor.ingest()
            print(f"DEBUG: Ingestor {ingestor.source_name} completed with {len(res)} results.")
            results.extend(res)
        except Exception as e:
            print(f"DEBUG: Ingestor '{ingestor.source_name}' failed: {e}")
            logger.error(f"Ingestor '{ingestor.source_name}' failed: {e}")

    # Export to S3
    if results:
        print(f"DEBUG: Exporting {len(results)} results to S3 for client {client_id}...")
        await exporter.export(client_id=client_id, results=results)
        print("DEBUG: Export completed successfully.")
    else:
        print("DEBUG: No results to export.")


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

    ingestors: List[BaseIngestor] = []
    if request.include_aws:
        ingestors.append(AWSIngestor(region_name=request.aws_region))
    
    if request.include_github:
        ingestors.append(GitHubIngestor(client_id=request.client_id, session=session))

    exporter = S3Exporter()

    background_tasks.add_task(
        run_export,
        client_id=request.client_id,
        ingestors=ingestors,
        exporter=exporter,
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
    try:
        results = await ingestor.ingest()
        label = f"github_link_export_{repo_url.split('/')[-1] if '/' in repo_url else 'repo'}"
        if results:
            await exporter.export(client_id=client_id, results=results, label=label)
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

    ingestor = GitHubLinkIngestor(repo_url=request.repo_url, branch=request.branch)
    exporter = S3Exporter()

    background_tasks.add_task(
        run_github_link,
        client_id=request.client_id,
        ingestor=ingestor,
        exporter=exporter,
        repo_url=request.repo_url,
    )

    return ExportResponse(
        status="started",
        message=f"GitHub link ingestion started for client {request.client_id}. Data will be exported to S3.",
    )
