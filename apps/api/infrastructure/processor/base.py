from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from uuid import UUID
from dataclasses import asdict

@dataclass
class ValidationWarning:
    type: str # e.g., 'empty_container', 'partial_scan'
    message: str
    severity: str # 'info', 'warn', 'error'

@dataclass
class IRNode:
    id: str # namespaced, e.g. "aws:s3:bucket-name"
    template_id: str
    display_name: str
    node_type: str # compute | storage | database | networking | security | messaging
    parent_id: Optional[str] = None
    source: str = "inferred" # "aws" | "github" | "inferred"
    confidence: float = 1.0
    source_completeness: str = "full" # "full" | "partial" | "inferred"
    source_metadata: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    environment: str = "unknown" # e.g. "prod", "staging", "dev"
    validation_warnings: List[ValidationWarning] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "display_name": self.display_name,
            "node_type": self.node_type,
            "parent_id": self.parent_id,
            "source": self.source,
            "confidence": self.confidence,
            "source_completeness": self.source_completeness,
            "source_metadata": self.source_metadata,
            "properties": self.properties,
            "environment": self.environment,
            "validation_warnings": [asdict(w) for w in self.validation_warnings] if hasattr(self, 'validation_warnings') else []
        }

@dataclass
class IREdge:
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str # "depends_on" | "accesses" | "mirrors" | "has_access_to" | "manages" | "routes_to" | "deploys_to"
    source: str # "aws" | "github" | "inferred"
    confidence: float
    environment: str = "unknown"
    properties: Dict[str, Any] = field(default_factory=dict)

class ProcessingContext:
    def __init__(self, raw_github: Dict[str, Any], raw_aws: Dict[str, Any]):
        self.raw_github = raw_github
        self.raw_aws = raw_aws
        self.nodes: Dict[str, IRNode] = {} # id -> Node
        self.edges: List[IREdge] = []
        self.graph_metadata: Dict[str, Any] = {
            "source_completeness": "full",
            "warnings": []
        }

class BaseStage:
    def run(self, context: ProcessingContext) -> ProcessingContext:
        raise NotImplementedError("Subclasses must implement run()")