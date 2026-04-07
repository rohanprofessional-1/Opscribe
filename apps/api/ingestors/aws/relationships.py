"""
Relationship detection between AWS topology nodes.

Strategies run in order:
  1. Property cross-reference  (confidence=inferred, source=property_scan)
  2. SDK-direct API calls      (confidence=explicit, source=sdk_direct)

Results are merged and deduplicated by (source_uid, target_uid, relation).
When duplicates exist, "explicit" confidence wins over "inferred".
"""

from __future__ import annotations

import re
import json
import logging
import asyncio
from typing import Any
from concurrent.futures import ThreadPoolExecutor

from botocore.exceptions import ClientError

from apps.api.ingestors.aws.schema import TopologyNode, TopologyEdge
from apps.api.ingestors.aws.client_factory import AWSClientFactory

logger = logging.getLogger(__name__)

# Keys to skip during property cross-reference scan
_SKIP_KEYS = frozenset({
    "service", "state", "status", "tags", "description",
    "name", "type", "region", "account_id",
})

# Regex for AWS resource ID patterns
_RESOURCE_ID_RE = re.compile(r"^(vpc|subnet|sg|i|vol|igw|rtb|acl|eni|nat)-[a-f0-9]+$")


class RelationshipDetector:
    """Detects edges between collected topology nodes."""

    def __init__(self, factory: AWSClientFactory, credentials: dict | None = None) -> None:
        self._factory = factory
        self._credentials = credentials or {}

    def detect(
        self,
        nodes: list[TopologyNode],
    ) -> list[TopologyEdge]:
        """Run all strategies, merge, and deduplicate."""
        edges: list[TopologyEdge] = []

        # Build lookup indexes
        id_index: dict[str, str] = {}    # raw resource id -> node uid
        arn_index: dict[str, str] = {}   # full ARN -> node uid

        for n in nodes:
            # Index by resource_id from merge_hints
            rid = n.merge_hints.get("resource_id")
            if rid:
                id_index[rid] = n.uid

            # Index by ARN
            arn = n.merge_hints.get("arn")
            if arn:
                arn_index[arn] = n.uid

            # Also index the uid's last segment (the resource id portion)
            parts = n.uid.split("::")
            if len(parts) >= 4:
                id_index[parts[-1]] = n.uid

        # Strategy 1: Property cross-reference
        edges.extend(self._from_property_scan(nodes, id_index, arn_index))

        # Strategy 2: SDK-direct
        edges.extend(self._from_sdk_direct(nodes, id_index, arn_index))

        return self._deduplicate(edges)

    # -----------------------------------------------------------------------
    # Strategy 1: Property cross-reference
    # -----------------------------------------------------------------------

    def _from_property_scan(
        self,
        nodes: list[TopologyNode],
        id_index: dict[str, str],
        arn_index: dict[str, str],
    ) -> list[TopologyEdge]:
        """Walk every node's properties recursively looking for ARN / resource-ID references."""
        edges: list[TopologyEdge] = []

        for node in nodes:
            found = self._scan_dict(node.properties, id_index, arn_index)
            for target_uid in found:
                if target_uid != node.uid:
                    edges.append(TopologyEdge(
                        uid=TopologyEdge.make_uid(node.uid, target_uid, "references"),
                        source_uid=node.uid,
                        target_uid=target_uid,
                        relation="references",
                        confidence="inferred",
                        source="property_scan",
                        metadata={},
                    ))

        return edges

    def _scan_dict(
        self,
        data: dict | list | Any,
        id_index: dict[str, str],
        arn_index: dict[str, str],
    ) -> set[str]:
        """Recursively scan a dict/list for references. Returns set of target uids."""
        targets: set[str] = set()

        if isinstance(data, dict):
            for key, val in data.items():
                if key in _SKIP_KEYS:
                    continue
                targets.update(self._scan_dict(val, id_index, arn_index))

        elif isinstance(data, list):
            for item in data:
                targets.update(self._scan_dict(item, id_index, arn_index))

        elif isinstance(data, str):
            # ARN reference
            if data.startswith("arn:aws:"):
                uid = arn_index.get(data)
                if uid:
                    targets.add(uid)

            # Resource ID reference (vpc-xxx, i-xxx, etc.)
            elif _RESOURCE_ID_RE.match(data):
                uid = id_index.get(data)
                if uid:
                    targets.add(uid)

            # SQS queue URL pattern
            elif "sqs." in data and "amazonaws.com" in data:
                qname = data.rstrip("/").split("/")[-1]
                uid = id_index.get(qname)
                if uid:
                    targets.add(uid)

        return targets

    # -----------------------------------------------------------------------
    # Strategy 2: SDK-direct
    # -----------------------------------------------------------------------

    def _from_sdk_direct(
        self,
        nodes: list[TopologyNode],
        id_index: dict[str, str],
        arn_index: dict[str, str],
    ) -> list[TopologyEdge]:
        """Extra SDK-direct and specialized relationship logic."""
        edges: list[TopologyEdge] = []
        edges.extend(self._elb_to_ec2(nodes, id_index, arn_index))
        edges.extend(self._cloudtrail_to_s3(nodes, id_index))
        edges.extend(self._cloudfront_to_s3(nodes, id_index))
        edges.extend(self._eventbridge_to_targets(nodes, arn_index))
        edges.extend(self._s3_to_lambda(nodes, arn_index))
        edges.extend(self._lambda_env_scan(nodes, id_index))
        return edges

    # -- ELB → EC2 via target group resolution (NOT shared VPC) --

    def _elb_to_ec2(
        self,
        nodes: list[TopologyNode],
        id_index: dict[str, str],
        arn_index: dict[str, str],
    ) -> list[TopologyEdge]:
        edges: list[TopologyEdge] = []
        elb_nodes = [n for n in nodes if n.service == "ELB"]
        if not elb_nodes:
            return edges

        # Group ELBs by region so we use the correct regional client
        elb_by_region: dict[str, list[TopologyNode]] = {}
        for lb in elb_nodes:
            elb_by_region.setdefault(lb.region, []).append(lb)

        for region, lbs in elb_by_region.items():
            try:
                regional_factory = AWSClientFactory(region, self._credentials)
                elbv2 = regional_factory.get_client("elbv2")

                for lb_node in lbs:
                    lb_arn = lb_node.merge_hints.get("arn")
                    if not lb_arn:
                        continue

                    try:
                        tg_resp = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
                    except ClientError:
                        continue

                    for tg in tg_resp.get("TargetGroups", []):
                        tg_arn = tg["TargetGroupArn"]
                        try:
                            health_resp = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                        except ClientError:
                            continue

                        for desc in health_resp.get("TargetHealthDescriptions", []):
                            target_id = desc.get("Target", {}).get("Id", "")
                            target_uid = id_index.get(target_id)
                            if target_uid and target_uid != lb_node.uid:
                                edges.append(TopologyEdge(
                                    uid=TopologyEdge.make_uid(lb_node.uid, target_uid, "routes_to"),
                                    source_uid=lb_node.uid,
                                    target_uid=target_uid,
                                    relation="routes_to",
                                    confidence="explicit",
                                    source="sdk_direct",
                                    metadata={"target_group_arn": tg_arn},
                                ))
            except Exception as e:
                logger.warning(f"ELB→EC2 SDK-direct detection error in {region}: {e}")

        return edges

    # -- CloudTrail → S3 --

    def _cloudtrail_to_s3(
        self,
        nodes: list[TopologyNode],
        id_index: dict[str, str],
    ) -> list[TopologyEdge]:
        edges: list[TopologyEdge] = []
        for n in nodes:
            if n.service != "CloudTrail":
                continue
            bucket = n.properties.get("s3_bucket_name")
            if not bucket:
                continue
            target_uid = id_index.get(bucket)
            if target_uid:
                edges.append(TopologyEdge(
                    uid=TopologyEdge.make_uid(n.uid, target_uid, "writes_to"),
                    source_uid=n.uid,
                    target_uid=target_uid,
                    relation="writes_to",
                    confidence="explicit",
                    source="sdk_direct",
                    metadata={},
                ))
        return edges

    # -- CloudFront → S3 origins --

    def _cloudfront_to_s3(
        self,
        nodes: list[TopologyNode],
        id_index: dict[str, str],
    ) -> list[TopologyEdge]:
        edges: list[TopologyEdge] = []
        for n in nodes:
            if n.service != "CloudFront":
                continue
            for origin in n.properties.get("origins", []):
                if not isinstance(origin, str):
                    continue
                if ".s3." in origin or origin.endswith(".s3.amazonaws.com"):
                    bucket_name = origin.split(".")[0]
                    target_uid = id_index.get(bucket_name)
                    if target_uid:
                        edges.append(TopologyEdge(
                            uid=TopologyEdge.make_uid(n.uid, target_uid, "originates_from"),
                            source_uid=n.uid,
                            target_uid=target_uid,
                            relation="originates_from",
                            confidence="explicit",
                            source="sdk_direct",
                            metadata={},
                        ))
        return edges

    # -- EventBridge → targets --

    def _eventbridge_to_targets(
        self,
        nodes: list[TopologyNode],
        arn_index: dict[str, str],
    ) -> list[TopologyEdge]:
        edges: list[TopologyEdge] = []
        eb_nodes = [n for n in nodes if n.service == "EventBridge"]
        if not eb_nodes:
            return edges

        # Group by region for correct regional client
        eb_by_region: dict[str, list[TopologyNode]] = {}
        for eb in eb_nodes:
            eb_by_region.setdefault(eb.region, []).append(eb)

        for region, ebs in eb_by_region.items():
            try:
                regional_factory = AWSClientFactory(region, self._credentials)
                events = regional_factory.get_client("events")

                for eb_node in ebs:
                    rule_name = eb_node.properties.get("rule_name")
                    if not rule_name:
                        continue

                    try:
                        resp = events.list_targets_by_rule(Rule=rule_name)
                    except ClientError:
                        continue

                    for target in resp.get("Targets", []):
                        target_arn = target.get("Arn", "")
                        target_uid = arn_index.get(target_arn)
                        if target_uid and target_uid != eb_node.uid:
                            edges.append(TopologyEdge(
                                uid=TopologyEdge.make_uid(eb_node.uid, target_uid, "routes_to"),
                                source_uid=eb_node.uid,
                                target_uid=target_uid,
                                relation="routes_to",
                                confidence="explicit",
                                source="sdk_direct",
                                metadata={"target_id": target.get("Id")},
                            ))
            except Exception as e:
                logger.warning(f"EventBridge→targets SDK-direct detection error in {region}: {e}")

        return edges

    # -- S3 Notifications → Lambda --

    def _s3_to_lambda(
        self,
        nodes: list[TopologyNode],
        arn_index: dict[str, str],
    ) -> list[TopologyEdge]:
        edges: list[TopologyEdge] = []
        for n in nodes:
            if n.service != "S3":
                continue
            for lambda_arn in n.properties.get("lambda_triggers", []):
                target_uid = arn_index.get(lambda_arn)
                # S3 event notification ARN might contain an alias suffix
                if not target_uid and ":" in lambda_arn:
                    # Strip suffix and try again (e.g. arn:aws:lambda:...:function:my-func:Alias)
                    base_arn = ":".join(lambda_arn.split(":")[:7])
                    target_uid = arn_index.get(base_arn)

                if target_uid:
                    edges.append(TopologyEdge(
                        uid=TopologyEdge.make_uid(n.uid, target_uid, "triggers"),
                        source_uid=n.uid,
                        target_uid=target_uid,
                        relation="triggers",
                        confidence="explicit",
                        source="sdk_direct",
                        metadata={"trigger_type": "s3_notification"},
                    ))
        return edges

    # -- Lambda ENV → S3 --

    def _lambda_env_scan(
        self,
        nodes: list[TopologyNode],
        id_index: dict[str, str],
    ) -> list[TopologyEdge]:
        """Scan lambda environment variables specifically for references to known S3 buckets."""
        edges: list[TopologyEdge] = []
        
        # Pre-filter all S3 bucket names in our graph
        s3_bucket_names = {
            n.name: n.uid
            for n in nodes
            if n.service == "S3"
        }

        if not s3_bucket_names:
            return edges

        for n in nodes:
            if n.service != "Lambda":
                continue
            env_vars = n.properties.get("environment", {})
            for key, val in env_vars.items():
                if not isinstance(val, str):
                    continue
                
                # Check if the environment variable perfectly matches an S3 bucket name
                if val in s3_bucket_names:
                    target_uid = s3_bucket_names[val]
                    edges.append(TopologyEdge(
                        uid=TopologyEdge.make_uid(n.uid, target_uid, "references"),
                        source_uid=n.uid,
                        target_uid=target_uid,
                        relation="references",
                        confidence="inferred",
                        source="sdk_direct",
                        metadata={"env_var_key": key},
                    ))
        return edges

    # -----------------------------------------------------------------------
    # Deduplication
    # -----------------------------------------------------------------------

    @staticmethod
    def _deduplicate(edges: list[TopologyEdge]) -> list[TopologyEdge]:
        """Deduplicate by (source_uid, target_uid, relation). Prefer explicit confidence."""
        best: dict[tuple[str, str, str], TopologyEdge] = {}
        for e in edges:
            key = (e.source_uid, e.target_uid, e.relation)
            existing = best.get(key)
            if existing is None:
                best[key] = e
            elif existing.confidence == "inferred" and e.confidence == "explicit":
                best[key] = e
        return list(best.values())
