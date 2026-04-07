"""
AWS infrastructure detector — thin orchestrator with multi-region scanning.

Discovers active regions via ec2.describe_regions, then scans all regional
collectors in parallel via asyncio.run_in_executor. Global collectors
(IAM, CloudFront, S3) run once using the bootstrap region client.
"""

from __future__ import annotations

import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from apps.api.ingestors.aws.base import BaseDetector
from apps.api.ingestors.aws.schemas import DiscoveryResult
from apps.api.ingestors.aws.schema import TopologyNode, TopologyEdge, TopologyScan
from apps.api.ingestors.aws.client_factory import AWSClientFactory
from apps.api.ingestors.aws.relationships import RelationshipDetector

# Collectors
from apps.api.ingestors.aws.collectors.compute import (
    EC2Collector, LambdaCollector, ECSCollector, EKSCollector,
)
from apps.api.ingestors.aws.collectors.storage import (
    S3Collector, EBSCollector, EFSCollector, FSxCollector,
)
from apps.api.ingestors.aws.collectors.database import (
    RDSCollector, DynamoDBCollector, RedshiftCollector,
)
from apps.api.ingestors.aws.collectors.networking import (
    VPCCollector, ELBCollector, CloudFrontCollector, DirectConnectCollector,
)
from apps.api.ingestors.aws.collectors.security import (
    IAMCollector, KMSCollector, SecretsManagerCollector, DirectoryServiceCollector,
)
from apps.api.ingestors.aws.collectors.observability import (
    CloudWatchCollector, CloudTrailCollector, SSMCollector,
)
from apps.api.ingestors.aws.collectors.integration import (
    SQSCollector, SNSCollector, EventBridgeCollector, APIGatewayCollector,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Collector classification — module-level constants
# ---------------------------------------------------------------------------

REGIONAL_COLLECTORS = [
    EC2Collector, LambdaCollector, ECSCollector, EKSCollector,
    EBSCollector, EFSCollector, FSxCollector,
    RDSCollector, DynamoDBCollector, RedshiftCollector,
    VPCCollector, ELBCollector, DirectConnectCollector,
    KMSCollector, SecretsManagerCollector, DirectoryServiceCollector,
    CloudWatchCollector, CloudTrailCollector, SSMCollector,
    SQSCollector, SNSCollector, EventBridgeCollector, APIGatewayCollector,
]

GLOBAL_COLLECTORS = [
    IAMCollector,
    CloudFrontCollector,
    S3Collector,
]


# ---------------------------------------------------------------------------
# Region discovery helper
# ---------------------------------------------------------------------------

class RegionDiscovery:
    """Discover active AWS regions for the account."""

    def __init__(self, factory: AWSClientFactory) -> None:
        self._factory = factory

    def get_active_regions(self) -> list[str]:
        """Return all regions the account has opted into."""
        ec2 = self._factory.get_client("ec2")
        response = ec2.describe_regions(
            Filters=[{
                "Name": "opt-in-status",
                "Values": ["opt-in-not-required", "opted-in"],
            }]
        )
        return [r["RegionName"] for r in response.get("Regions", [])]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AWSDetector(BaseDetector):
    """Comprehensive AWS infrastructure detector with multi-region scanning.

    - bootstrap_region (region_name) is used only for STS, describe_regions,
      and global collectors.
    - Regional collectors are instantiated per-region in parallel threads.
    """

    def __init__(self, region_name: str | None = "us-east-1", credentials: dict | None = None) -> None:
        self.region_name = region_name or "us-east-1"  # bootstrap region
        self.credentials = credentials or {}

        # Bootstrap factory — used for STS, describe_regions, and global collectors
        self._factory = AWSClientFactory(region_name=region_name, credentials=self.credentials)

        # Resolve account ID eagerly
        self.account_id = self._get_account_id()

        # Global collectors (run once with bootstrap factory)
        self._global_collectors = [
            Cls(self._factory, region_name, self.account_id)
            for Cls in GLOBAL_COLLECTORS
        ]

        # Relationship detector
        self._relationship_detector = RelationshipDetector(self._factory, self.credentials)

    # -- Public API ----------------------------------------------------------

    @property
    def source_name(self) -> str:
        return "aws"

    async def discover(self, include_relationships: bool = True, **kwargs: Any) -> DiscoveryResult:
        """Run full multi-region scan and return legacy DiscoveryResult."""
        scan = await self._run_scan(include_relationships)
        return scan.to_discovery_result()

    async def scan_to_json(self, output_path: str | None = None, **kwargs: Any) -> str:
        """Run full multi-region scan and return the TopologyScan JSON snapshot.

        If *output_path* is provided, also writes the JSON file.
        This is the primary output method for the datalake pipeline.
        """
        include_relationships = kwargs.get("include_relationships", True)
        scan = await self._run_scan(include_relationships)
        json_str = scan.to_json()

        if output_path:
            with open(output_path, "w") as f:
                f.write(json_str)
            logger.info(f"Scan JSON written to {output_path}")

        return json_str

    # -- Internals -----------------------------------------------------------

    def _get_account_id(self) -> str:
        """Resolve AWS account ID via STS."""
        try:
            sts = self._factory.get_client("sts")
            return sts.get_caller_identity()["Account"]
        except Exception as e:
            logger.warning(f"Could not retrieve account ID: {e}")
            return "000000000000"

    async def _run_scan(self, include_relationships: bool) -> TopologyScan:
        """Core scanning logic: parallel regional + synchronous global."""
        all_nodes: list[TopologyNode] = []
        edges: list[TopologyEdge] = []

        try:
            # Discover active regions
            active_regions = RegionDiscovery(self._factory).get_active_regions()
            logger.info(f"Scanning {len(active_regions)} regions: {active_regions}")

            # --- Regional collectors: run concurrently across regions ---
            loop = asyncio.get_event_loop()
            regional_tasks = [
                loop.run_in_executor(None, self._scan_region, region)
                for region in active_regions
            ]
            regional_results = await asyncio.gather(*regional_tasks, return_exceptions=True)

            for region, result in zip(active_regions, regional_results):
                if isinstance(result, Exception):
                    logger.error(f"Region {region} scan failed: {result}")
                    continue
                logger.info(f"Region {region}: {len(result)} nodes")
                all_nodes.extend(result)

            # --- Global collectors: run once (synchronously — they're fast) ---
            for collector in self._global_collectors:
                name = type(collector).__name__
                logger.info(f"Running {name} (global)...")
                collected = collector.collect()
                logger.info(f"  {name}: {len(collected)} nodes")
                all_nodes.extend(collected)

            # Deduplicate by uid (guards against edge cases)
            seen: dict[str, TopologyNode] = {}
            for node in all_nodes:
                seen[node.uid] = node
            all_nodes = list(seen.values())

            logger.info(f"Total unique nodes: {len(all_nodes)}")

            if include_relationships:
                logger.info("Detecting resource relationships...")
                edges = self._relationship_detector.detect(all_nodes)
                logger.info(f"  Detected {len(edges)} relationships")
            else:
                logger.info("Skipping relationship detection for datalake population.")

        except Exception as e:
            logger.error(f"AWS discovery failed: {e}", exc_info=True)
            active_regions = [self.region_name]

        return TopologyScan(
            scan_id=str(uuid.uuid4()),
            provider="aws",
            account_id=self.account_id,
            regions_scanned=active_regions,
            scanned_at=datetime.now(timezone.utc).isoformat(),
            nodes=all_nodes,
            edges=edges,
        )

    def _scan_region(self, region: str) -> list[TopologyNode]:
        """Scan a single region — runs in a thread via run_in_executor."""
        regional_factory = AWSClientFactory(region, self.credentials)
        nodes: list[TopologyNode] = []

        for CollectorClass in REGIONAL_COLLECTORS:
            collector = CollectorClass(regional_factory, region, self.account_id)
            name = CollectorClass.__name__
            try:
                collected = collector.collect()
                if collected:
                    logger.info(f"  {region}/{name}: {len(collected)} nodes")
                nodes.extend(collected)
            except Exception as e:
                logger.warning(f"  {region}/{name} failed: {e}")

        return nodes
