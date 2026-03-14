from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from uuid import UUID

class DiscoveryNode(BaseModel):
    key: str
    display_name: Optional[str] = None
    node_type: str # Canonical name: service, host, datastore, etc.
    properties: Dict[str, Any] = {}
    source_metadata: Dict[str, Any] = {}

class DiscoveryEdge(BaseModel):
    from_node_key: str
    to_node_key: str
    edge_type: str # Canonical name: calls, depends_on, etc.
    properties: Dict[str, Any] = {}

class DiscoveryResult(BaseModel):
    source: str
    nodes: List[DiscoveryNode] = []
    edges: List[DiscoveryEdge] = []
    metadata: Dict[str, Any] = {}
