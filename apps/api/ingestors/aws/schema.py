"""
Topology dataclasses for the AWS ingestor JSON output.

These are the NEW schema types used for the datalake JSON snapshot.
The legacy DiscoveryNode / DiscoveryEdge / DiscoveryResult in schemas.py
are preserved for backwards compatibility — see to_discovery_result().
"""

from __future__ import annotations

import json
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from apps.api.ingestors.aws.schemas import DiscoveryResult, DiscoveryNode, DiscoveryEdge


# ---------------------------------------------------------------------------
# TopologyNode
# ---------------------------------------------------------------------------

@dataclass
class TopologyNode:
    uid: str                   # aws::{region}::{service_prefix}::{resource_id}
    provider: str
    service: str
    resource_type: str         # normalized cross-provider type
    category: str
    name: str                  # best available display name
    region: str
    account_id: str
    tags: dict = field(default_factory=dict)
    merge_hints: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# TopologyEdge
# ---------------------------------------------------------------------------

@dataclass
class TopologyEdge:
    uid: str                   # deterministic hash of (source_uid, target_uid, relation)
    source_uid: str
    target_uid: str
    relation: str
    confidence: str            # "explicit" | "inferred"
    source: str                # "aws_config" | "property_scan" | "sdk_direct"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def make_uid(source_uid: str, target_uid: str, relation: str) -> str:
        """Deterministic edge uid from its triple."""
        raw = f"{source_uid}|{target_uid}|{relation}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# TopologyScan
# ---------------------------------------------------------------------------

def _json_default(obj: Any) -> Any:
    """Fallback serializer for datetime and other non-JSON types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


@dataclass
class TopologyScan:
    scan_id: str
    provider: str
    account_id: str
    regions_scanned: list[str]   # all regions that were scanned
    scanned_at: str              # ISO-8601
    nodes: list[TopologyNode] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)

    @property
    def region_count(self) -> int:
        return len(self.regions_scanned)

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "schema_version": "1.0",
            "scan": {
                "id": self.scan_id,
                "provider": self.provider,
                "account_id": self.account_id,
                "regions_scanned": self.regions_scanned,
                "region_count": self.region_count,
                "scanned_at": self.scanned_at,
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
            },
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_json_default)

    # -- Backwards-compat bridge ---------------------------------------------

    def to_discovery_result(self) -> DiscoveryResult:
        """Convert to the legacy DiscoveryResult expected by existing callers."""
        legacy_nodes: list[DiscoveryNode] = []
        for n in self.nodes:
            legacy_nodes.append(
                DiscoveryNode(
                    key=n.uid,
                    display_name=n.name,
                    node_type=n.category,
                    node_subtype=n.resource_type,
                    properties=n.properties,
                    source_metadata={
                        "arn": n.merge_hints.get("arn", ""),
                        **n.merge_hints,
                    },
                )
            )

        legacy_edges: list[DiscoveryEdge] = []
        for e in self.edges:
            legacy_edges.append(
                DiscoveryEdge(
                    from_node_key=e.source_uid,
                    to_node_key=e.target_uid,
                    edge_type=e.relation,
                    direction="outbound",
                    properties=e.metadata,
                )
            )

        return DiscoveryResult(
            source=self.provider,
            nodes=legacy_nodes,
            edges=legacy_edges,
            metadata={
                "regions_scanned": self.regions_scanned,
                "account_id": self.account_id,
                "scan_id": self.scan_id,
            },
        )
