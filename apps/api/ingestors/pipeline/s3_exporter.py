"""
S3 Exporter — Per-Tenant Data Export

Exports combined GitHub + AWS discovery results to S3 as JSON,
organized by client_id (tenant).

Auth: Uses env vars AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION.
On EC2/ECS with an attached IAM role, those can be omitted.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from apps.api.ingestors.aws.schemas import DiscoveryResult

logger = logging.getLogger(__name__)


class S3Exporter:
    """Exports DiscoveryResult data to S3 per client_id."""

    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
        self.bucket = os.environ.get("OPSCRIBE_S3_BUCKET", "opscribe-data")

    def _result_to_dict(self, result: DiscoveryResult) -> dict:
        """Serialize a DiscoveryResult to a JSON-serializable dict."""
        return {
            "source": result.source,
            "nodes": [
                {
                    "key": n.key,
                    "display_name": n.display_name,
                    "node_type": n.node_type,
                    "properties": n.properties,
                    "source_metadata": n.source_metadata,
                }
                for n in result.nodes
            ],
            "edges": [
                {
                    "from_node_key": e.from_node_key,
                    "to_node_key": e.to_node_key,
                    "edge_type": e.edge_type,
                    "properties": e.properties,
                }
                for e in result.edges
            ],
            "metadata": result.metadata,
        }

    async def export(
        self,
        client_id: str,
        results: list[DiscoveryResult],
        label: Optional[str] = None,
    ) -> str:
        """
        Export one or more DiscoveryResults to S3 for a given client_id.

        S3 key structure:
            {client_id}/latest.json        — most recent combined export
            {client_id}/history/{ts}.json   — timestamped archive

        Returns the S3 key of the exported file.
        """
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")

        payload = {
            "client_id": client_id,
            "label": label or "combined_export",
            "exported_at": now.isoformat(),
            "sources": [self._result_to_dict(r) for r in results],
            "summary": {
                "total_nodes": sum(len(r.nodes) for r in results),
                "total_edges": sum(len(r.edges) for r in results),
                "sources": [r.source for r in results],
            },
        }

        body = json.dumps(payload, indent=2, default=str)

        # Upload latest
        latest_key = f"{client_id}/latest.json"
        history_key = f"{client_id}/history/{timestamp}.json"

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=latest_key,
                Body=body.encode("utf-8"),
                ContentType="application/json",
            )
            logger.info(f"Uploaded to s3://{self.bucket}/{latest_key}")

            # Also archive
            self.s3.put_object(
                Bucket=self.bucket,
                Key=history_key,
                Body=body.encode("utf-8"),
                ContentType="application/json",
            )
            logger.info(f"Archived to s3://{self.bucket}/{history_key}")

            return latest_key

        except ClientError as e:
            logger.error(f"S3 upload failed for client {client_id}: {e}")
            raise
