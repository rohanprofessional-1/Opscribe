"""
AWS discovery schemas.

These mirror the canonical pipeline schemas but are defined inline
to avoid circular imports (aws.schemas ↔ pipeline.base ↔ aws.schemas).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class DiscoveryNode(BaseModel):
    key: str
    display_name: Optional[str] = None
    node_type: str  # Canonical: compute, datastore, network, storage, integration
    node_subtype: Optional[str] = None  # Specific: postgres, redis, backend_api
    properties: Dict[str, Any] = {}
    source_metadata: Dict[str, Any] = {}


class DiscoveryEdge(BaseModel):
    from_node_key: str
    to_node_key: str
    edge_type: str  # depends_on, imports, links, contains, communicates_with
    direction: str = "outbound"
    properties: Dict[str, Any] = {}


class DiscoveryResult(BaseModel):
    source: str
    nodes: List[DiscoveryNode] = []
    edges: List[DiscoveryEdge] = []
    metadata: Dict[str, Any] = {}
