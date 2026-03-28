"""
Canonical RAW-layer schemas for the ingestion pipeline.

These models define the contract between parsers → pipeline → S3 exporter.
All ingestion sources (GitHub, AWS, etc.) must emit data conforming to these schemas.

Schema version: raw_v1
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DiscoveryNode(BaseModel):
    """
    A single infrastructure entity extracted from source files.

    Spec §4 — Node Schema (RAW Layer)
    """
    key: str = Field(
        description="Globally unique identifier: github:{repo_full_name}:{entity_type}:{name}"
    )
    display_name: str = Field(
        description="Human-readable label for UI rendering"
    )
    node_type: str = Field(
        description="Coarse category: compute, datastore, network, storage, integration"
    )
    node_subtype: Optional[str] = Field(
        default=None,
        description="Specific classification: postgres, redis, backend_api, react_app, etc."
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw extracted fields from the source file"
    )
    source_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance: file, line_range, extraction_method, confidence, is_inferred"
    )


class DiscoveryEdge(BaseModel):
    """
    A relationship between two DiscoveryNodes.

    Spec §5 — Edge Schema (RAW Relationships)
    """
    from_node_key: str = Field(
        description="Key of the source node"
    )
    to_node_key: str = Field(
        description="Key of the target node"
    )
    edge_type: str = Field(
        description="Relationship type: depends_on, imports, links, contains, communicates_with"
    )
    direction: str = Field(
        default="outbound",
        description="Edge direction: outbound (default) or inbound"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source file, confidence, is_inferred flag"
    )


class DiscoveryResult(BaseModel):
    """
    The output of a single ingestion run for one source.

    Spec §2, §11 — Contains all nodes, edges, and metadata needed for replay.
    """
    source: str = Field(
        description="Source system identifier: github, aws, etc."
    )
    nodes: List[DiscoveryNode] = Field(
        default_factory=list
    )
    edges: List[DiscoveryEdge] = Field(
        default_factory=list
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline-level metadata: repo_url, branch, commit_sha, etc."
    )
