from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# Shared properties
class ClientBase(BaseModel):
    name: str
    metadata_: Dict[str, Any] = {}

class ClientCreate(ClientBase):
    pass

class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime

# Graph Schemas
class GraphBase(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Dict[str, Any] = {}

class GraphCreate(GraphBase):
    client_id: UUID

class GraphRead(GraphBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

# NodeType Schemas
class NodeTypeBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    allowed_properties: List[str] = []

class NodeTypeCreate(NodeTypeBase):
    client_id: UUID
    graph_id: UUID

class NodeTypeRead(NodeTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    graph_id: UUID
    created_at: datetime
    updated_at: datetime

# EdgeType Schemas
class EdgeTypeBase(BaseModel):
    name: str
    calls: bool = False
    depends_on: bool = False
    publishes_to: bool = False
    consumes_from: bool = False
    stores_in: bool = False
    owned_by: bool = False
    part_of: bool = False
    provided_by: bool = False
    description: Optional[str] = None
    semantics: Dict[str, Any] = {}
    allowed_properties: List[str] = []
    from_node_type_id: Optional[UUID] = None
    to_node_type_id: Optional[UUID] = None

class EdgeTypeCreate(EdgeTypeBase):
    client_id: UUID
    graph_id: UUID

class EdgeTypeRead(EdgeTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    graph_id: UUID
    created_at: datetime
    updated_at: datetime

# Node Schemas
class NodeBase(BaseModel):
    key: str
    display_name: Optional[str] = None
    properties: Dict[str, Any] = {}
    source: Optional[str] = None
    source_metadata: Dict[str, Any] = {}

class NodeCreate(NodeBase):
    client_id: UUID
    graph_id: UUID
    node_type_id: UUID

class NodeRead(NodeBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    graph_id: UUID
    node_type_id: UUID
    created_at: datetime
    updated_at: datetime

# Edge Schemas
class EdgeBase(BaseModel):
    properties: Dict[str, Any] = {}

class EdgeCreate(EdgeBase):
    client_id: UUID
    graph_id: UUID
    edge_type_id: UUID
    from_node_id: UUID
    to_node_id: UUID

class EdgeRead(EdgeBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    graph_id: UUID
    edge_type_id: UUID
    from_node_id: UUID
    to_node_id: UUID
    created_at: datetime
    updated_at: datetime

# Visualization Schema
class GraphVisualization(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nodes: List[NodeRead]
    edges: List[EdgeRead]
