"""
S3 Exporter — Per-Tenant Data Lake Export

Exports DiscoveryResult payloads to S3/MinIO as JSON, conforming to the
raw_v1 schema spec. Implements:

  - Partitioned storage: {client_id}/{source}/date=YYYY-MM-DD/hour=HH/ingestion_{uuid}.json
  - Latest pointer:      {client_id}/{source}/latest.json
  - Full ingestion_metadata envelope (Spec §2)
  - Real content_hash fingerprinting (Spec §3)
  - DiscoveryEdge serialization (Spec §5)

Auth: Uses env vars or .env file for S3 credentials.
"""

import os
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from collections import defaultdict
from dotenv import dotenv_values

import boto3
from botocore.exceptions import ClientError

from apps.api.ingestors.pipeline.schemas import DiscoveryResult, DiscoveryNode, DiscoveryEdge
from apps.api.ingestors.pipeline.base import BaseExporter

logger = logging.getLogger(__name__)


class S3Exporter(BaseExporter):
    """Exports DiscoveryResult data to S3 per client_id."""

    def __init__(self):
        env = dotenv_values("apps/api/.env")

        endpoint_url = env.get("AWS_S3_ENDPOINT_URL") or os.environ.get("AWS_S3_ENDPOINT_URL")
        region = env.get("AWS_REGION") or os.environ.get("AWS_REGION", "us-east-1")
        access_key = env.get("OPSCRIBE_MINIO_USER") or os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = env.get("OPSCRIBE_MINIO_PASSWORD") or os.environ.get("AWS_SECRET_ACCESS_KEY")

        client_kwargs = {
            "service_name": "s3",
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        self.s3 = boto3.client(**client_kwargs)
        self.bucket = env.get("OPSCRIBE_S3_BUCKET") or os.environ.get("OPSCRIBE_S3_BUCKET", "opscribe-data")
        logger.info(f"S3Exporter initialized: bucket={self.bucket}, endpoint={endpoint_url}")

    @property
    def backend_name(self) -> str:
        return "s3"

    # ── Serialization helpers ────────────────────────────────────────

    @staticmethod
    def _node_to_dict(n: DiscoveryNode) -> dict:
        """Serialize a DiscoveryNode per Spec §4."""
        d = {
            "key": n.key,
            "display_name": n.display_name,
            "node_type": n.node_type,
            "properties": n.properties,
            "source_metadata": n.source_metadata,
        }
        if n.node_subtype:
            d["node_subtype"] = n.node_subtype
        return d

    @staticmethod
    def _edge_to_dict(e) -> dict:
        """Serialize a DiscoveryEdge per Spec §5. Handles both typed and dict edges."""
        if isinstance(e, dict):
            return e
        return {
            "from_node_key": e.from_node_key,
            "to_node_key": e.to_node_key,
            "edge_type": e.edge_type,
            "direction": getattr(e, "direction", "outbound"),
            "properties": e.properties,
        }

    def _result_to_dict(self, result: DiscoveryResult) -> dict:
        """Serialize a full DiscoveryResult source block."""
        return {
            "source": result.source,
            "nodes": [self._node_to_dict(n) for n in result.nodes],
            "edges": [self._edge_to_dict(e) for e in result.edges],
            "metadata": result.metadata,
        }

    # ── Export ────────────────────────────────────────────────────────

    async def export(
        self,
        client_id: str,
        results: List[DiscoveryResult],
        label: Optional[str] = None,
    ) -> str:
        """
        Export DiscoveryResults to S3 for a given client_id.

        S3 key structure (Spec §9):
            {client_id}/{source}/latest.json
            {client_id}/{source}/date={YYYY-MM-DD}/hour={HH}/ingestion_{uuid}.json
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        hour_str = now.strftime("%H")
        ingestion_id = str(uuid.uuid4())

        grouped_results: dict[str, list[DiscoveryResult]] = defaultdict(list)
        for r in results:
            grouped_results[r.source].append(r)

        uploaded_keys: List[str] = []

        for source, source_results in grouped_results.items():
            first_meta = source_results[0].metadata if source_results else {}

            repo_url = first_meta.get("repo_url", "")
            commit_sha = first_meta.get("commit_sha", "")
            content_hash = first_meta.get("content_hash", "")

            # ── Full ingestion_metadata envelope (Spec §2) ───────────
            payload = {
                "schema_version": "raw_v1",
                "ingestion_metadata": {
                    "ingestion_id": ingestion_id,
                    "pipeline_version": "v1",
                    "source": source,
                    "client_id": client_id,
                    "repo_full_name": first_meta.get("repo_full_name", ""),
                    "repo_url": repo_url,
                    "repo_id": first_meta.get("repo_id", ""),
                    "installation_id": first_meta.get("installation_id", ""),
                    "branch": first_meta.get("branch", "main"),
                    "commit_sha": commit_sha,
                    "ingestion_type": first_meta.get("ingestion_type", "manual"),
                    "triggered_at": now.isoformat(),
                },
                # ── Fingerprint (Spec §3) ────────────────────────────
                "fingerprint": {
                    "repo": repo_url,
                    "commit_sha": commit_sha,
                    "content_hash": content_hash,
                },
                "label": label or f"{source}_export",
                "exported_at": now.isoformat(),
                # ── Source data ───────────────────────────────────────
                "sources": [self._result_to_dict(r) for r in source_results],
                # ── Summary (Spec §8) ────────────────────────────────
                "summary": {
                    "total_nodes": sum(len(r.nodes) for r in source_results),
                    "total_edges": sum(len(r.edges) for r in source_results),
                    "sources": [source],
                },
            }

            body = json.dumps(payload, indent=2, default=str)

            latest_key = f"{client_id}/{source}/latest.json"
            history_key = (
                f"{client_id}/{source}/date={date_str}/hour={hour_str}"
                f"/ingestion_{ingestion_id}.json"
            )

            try:
                # Upload latest pointer
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=latest_key,
                    Body=body.encode("utf-8"),
                    ContentType="application/json",
                )
                logger.info(f"[STEP 7] Uploaded to s3://{self.bucket}/{latest_key}")

                # Archive immutable snapshot
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=history_key,
                    Body=body.encode("utf-8"),
                    ContentType="application/json",
                )
                logger.info(f"[STEP 7] Archived to s3://{self.bucket}/{history_key}")

                uploaded_keys.append(latest_key)

            except ClientError as e:
                logger.error(f"S3 upload failed for {source} client {client_id}: {e}")
                raise

        return ",".join(uploaded_keys)
