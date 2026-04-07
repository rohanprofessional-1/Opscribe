"""
Concrete ingestor implementations wrapping various data sources.
"""

import logging
from typing import List, Optional
from sqlmodel import Session, select

from apps.api.models import utc_now, ConnectedRepository
from apps.api.ingestors.aws.detector import AWSDetector
from apps.api.ingestors.aws.schemas import DiscoveryResult
from apps.api.ingestors.github.pipeline import GitHubIngestionPipeline
from apps.api.ingestors.github.app_auth import get_installation_token
from apps.api.ingestors.pipeline.base import BaseIngestor


logger = logging.getLogger(__name__)


class AWSIngestor(BaseIngestor):
    def __init__(self, region_name: str | None = "us-east-1", credentials: dict = None):
        self.region_name = region_name or "us-east-1"
        self.credentials = credentials or {}

    @property
    def source_name(self) -> str:
        return "aws"

    async def ingest(self) -> List[DiscoveryResult]:
        try:
            detector = AWSDetector(region_name=self.region_name, credentials=self.credentials)
            result = await detector.discover()
            return [result]
        except Exception as e:
            logger.error(f"AWSIngestor failed: {e}")
            return []


class GitHubIngestor(BaseIngestor):
    def __init__(self, client_id: str, session: Session, repo_url: Optional[str] = None):
        self.client_id = client_id
        self.session = session
        self.repo_url = repo_url

    @property
    def source_name(self) -> str:
        return "github"

    async def ingest(self) -> List[DiscoveryResult]:
        statement = select(ConnectedRepository).where(
            ConnectedRepository.client_id == self.client_id,
        )
        if self.repo_url:
            statement = statement.where(ConnectedRepository.repo_url == self.repo_url)
        
        repos = self.session.exec(statement).all()

        results: List[DiscoveryResult] = []
        for repo in repos:
            logger.info(f"Processing repo: {repo.repo_url}")
            repo.ingestion_status = "running"
            self.session.add(repo)
            self.session.commit()

            try:
                token = await get_installation_token(repo.installation_id, str(self.client_id), self.session)
                pipeline = GitHubIngestionPipeline(
                    repo_url=repo.repo_url,
                    branch=repo.default_branch or "main",
                    access_token=token,
                )
                result = await pipeline.run()
                
                # Enrich metadata with client-specific context (Spec §2)
                repo_full_name = (
                    repo.repo_url.split("github.com/")[-1]
                    if "github.com/" in repo.repo_url
                    else repo.repo_url
                )
                result.metadata.update({
                    "installation_id": repo.installation_id,
                    "repo_full_name": repo_full_name,
                    "repo_url": repo.repo_url,
                    "repo_id": str(getattr(repo, "repo_id", "")),
                    "ingestion_type": "manual",
                })
                
                logger.info(
                    f"Pipeline complete for {repo.repo_url}: "
                    f"{len(result.nodes)} nodes, {len(result.edges)} edges"
                )
                results.append(result)
                
                repo.ingestion_status = "success"
                repo.last_ingested_at = utc_now()
                self.session.add(repo)
                self.session.commit()

            except Exception as e:
                repo.ingestion_status = "failed"
                self.session.add(repo)
                self.session.commit()
                logger.error(f"GitHub ingestion failed for {repo.repo_url}: {e}")

        return results


class GitHubLinkIngestor(BaseIngestor):
    def __init__(self, repo_url: str, branch: str = "main"):
        self.repo_url = repo_url
        self.branch = branch

    @property
    def source_name(self) -> str:
        return "github_link"

    async def ingest(self) -> List[DiscoveryResult]:
        try:
            pipeline = GitHubIngestionPipeline(
                repo_url=self.repo_url,
                branch=self.branch,
                access_token="",
            )
            result = await pipeline.run()
            
            logger.info(
                f"GitHub link ingestion for {self.repo_url}: "
                f"{len(result.nodes)} nodes, {len(result.edges)} edges"
            )
            return [result]
        except Exception as e:
            logger.error(f"GitHub link ingestion failed for {self.repo_url}: {e}")
            return []
