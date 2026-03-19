"""
Pipeline Router — Triggers per-tenant data export to S3.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional, List

from apps.api.database import get_session
from apps.api.models import Client, ConnectedRepository, ClientIntegration
from apps.api.utils.encryption import decrypt_dict

# ... existing code ...

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

    # Keys to decrypt if present
    sensitive_keys = ["aws_secret_access_key", "secret_key"]

    ingestors: List[BaseIngestor] = []
    if request.include_aws:
        aws_creds = decrypt_dict(aws_integration.credentials, sensitive_keys) if aws_integration else {}
        ingestors.append(AWSIngestor(region_name=request.aws_region, credentials=aws_creds))
    
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
