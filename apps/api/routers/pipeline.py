"""
Pipeline Router — Triggers per-tenant data export to S3.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

from apps.api.database import engine, get_session
from apps.api.models import Client, ConnectedRepository, ClientIntegration
from apps.api.utils.encryption import decrypt_dict

import logging
from apps.api.routers.integrations import SENSITIVE_KEYS
from apps.api.ingestors.pipeline.ingestors import AWSIngestor, GitHubIngestor, GitHubLinkIngestor
from apps.api.ingestors.pipeline.s3_exporter import S3Exporter
from apps.api.ingestors.pipeline.base import BaseIngestor, BaseExporter
from apps.api.infrastructure.intermediate import ingest_to_all_clients

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pipeline",
    tags=["pipeline"],
)

class ExportRequest(BaseModel):
    client_id: str
    include_aws: bool = True
    include_github: bool = True

class GithubLinkRequest(BaseModel):
    client_id: UUID
    repo_url: str
    branch: Optional[str] = "main"

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
            await exporter.export(client_id=client_id, results=results, label="export")
            
            # Post-export: Ingest to graph for visualization
            # We pull the combined state from MinIO to ensure both AWS + GitHub are represented
            combined_results = await exporter.load_current(client_id=client_id)
            if combined_results:
                with Session(engine) as session:
                    await ingest_to_all_clients(results=combined_results, original_client_id=client_id, session=session)
            else:
                logger.warning(f"No current state results found for client {client_id} despite successful export.")
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

    ingestors: List[BaseIngestor] = []
    if request.include_aws:
        aws_creds = decrypt_dict(aws_integration.credentials, SENSITIVE_KEYS) if aws_integration else {}
        ingestors.append(AWSIngestor(region_name="us-east-1", credentials=aws_creds))
    
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

@router.post("/github-link", response_model=ExportResponse)
async def trigger_github_link(
    request: GithubLinkRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Trigger a background ingestion of a public GitHub URL directly to S3."""
    logger.info(f"Triggering public GitHub ingestion for client {request.client_id} (URL: {request.repo_url})")
    
    client = session.get(Client, request.client_id)
    if not client:
        logger.warning(f"Public ingestion failed: Client ID {request.client_id} not found in database.")
        raise HTTPException(status_code=404, detail=f"Client {request.client_id} not found. Please ensure your tenant ID is correct.")

    # Fetch active AWS integration to combine with GitHub Link results
    aws_integration = session.exec(
        select(ClientIntegration).where(
            ClientIntegration.client_id == str(request.client_id),
            ClientIntegration.provider == "aws",
            ClientIntegration.is_active == True
        )
    ).first()

    aws_creds = decrypt_dict(aws_integration.credentials, SENSITIVE_KEYS) if aws_integration else {}
    
    ingestors: List[BaseIngestor] = [
        GitHubLinkIngestor(repo_url=request.repo_url, branch=request.branch),
        AWSIngestor(region_name="us-east-1", credentials=aws_creds)
    ]
    exporter = S3Exporter()

    background_tasks.add_task(
        run_export, # Use run_export instead of run_github_link to handle multiple ingestors
        client_id=str(request.client_id),
        ingestors=ingestors,
        exporter=exporter,
    )

    return ExportResponse(
        status="started",
        message=f"GitHub link ingestion started for client {request.client_id}. Data will be exported to S3.",
    )
