from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, ARRAY, String
from sqlalchemy import Column, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB

# Shared properties or mixins could be defined here, but keeping it explicit for now.
def utc_now():
    return datetime.utcnow()


class PlatformConfig(SQLModel, table=True):
    """
    A single-row-per-key store for platform-wide server configuration.
    Sensitive values (e.g. private keys) are encrypted using the OPSCRIBE_MASTER_KEY
    before being saved here via the admin endpoints.
    """
    __tablename__ = "platform_config"
    key: str = Field(primary_key=True)   # e.g. "github_app_id"
    value: str = Field()                  # encrypted for sensitive entries
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})

class Client(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})
    metadata_: Dict[str, Any] = Field(default={}, sa_column=Column("metadata", JSONB))

    graphs: List["Graph"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    node_types: List["NodeType"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    edge_types: List["EdgeType"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    nodes: List["Node"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    edges: List["Edge"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    connected_repositories: List["ConnectedRepository"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    integrations: List["ClientIntegration"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ClientIntegration(SQLModel, table=True):
    __tablename__ = "client_integration"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", ondelete="CASCADE")
    provider: str = Field(index=True) # e.g. 'aws', 's3', 'datadog'
    credentials: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB)) # e.g. access_key, secret_key, region, bucket_name
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})

    client: Client = Relationship(back_populates="integrations")

    __table_args__ = (
        UniqueConstraint("client_id", "provider", name="unique_client_provider_integration"),
    )


class ConnectedRepository(SQLModel, table=True):
    __tablename__ = "connected_repository"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id")
    repo_url: str
    default_branch: str
    installation_id: str
    target_repo_id: str
    last_ingested_at: Optional[datetime] = None
    ingestion_status: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})

    client: Client = Relationship(back_populates="connected_repositories")

class Graph(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", ondelete="CASCADE")
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})
    settings: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB)) # layout defaults, visibility flags

    client: Client = Relationship(back_populates="graphs")
    node_types: List["NodeType"] = Relationship(back_populates="graph", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    edge_types: List["EdgeType"] = Relationship(back_populates="graph", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    nodes: List["Node"] = Relationship(back_populates="graph", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    edges: List["Edge"] = Relationship(back_populates="graph", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class NodeType(SQLModel, table=True):
    __tablename__ = "node_type"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", ondelete="CASCADE")
    graph_id: UUID = Field(foreign_key="graph.id", ondelete="CASCADE")
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    allowed_properties: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})

    client: Client = Relationship(back_populates="node_types")
    graph: Graph = Relationship(back_populates="node_types")
    nodes: List["Node"] = Relationship(back_populates="node_type")
    
    # Relationships for EdgeType definitions
    # These are a bit complex to reverse map cleanly in SQLModel without manual string joins, 
    # but we can define them if needed. For now, we rely on the EdgeType foreign keys.


class EdgeType(SQLModel, table=True):
    __tablename__ = "edge_type"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", ondelete="CASCADE")
    graph_id: UUID = Field(foreign_key="graph.id", ondelete="CASCADE")
    name: str
    
    # Relationship types / categorization
    calls: bool = False
    depends_on: bool = False
    publishes_to: bool = False
    consumes_from: bool = False
    stores_in: bool = False
    owned_by: bool = False
    part_of: bool = False
    provided_by: bool = False
    
    description: Optional[str] = None
    
    # Constraint references
    from_node_type_id: Optional[UUID] = Field(default=None, foreign_key="node_type.id")
    to_node_type_id: Optional[UUID] = Field(default=None, foreign_key="node_type.id")
    
    semantics: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB)) # data_flow, structural, ownership, vendor, grouping
    allowed_properties: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})

    client: Client = Relationship(back_populates="edge_types")
    graph: Graph = Relationship(back_populates="edge_types")
    edges: List["Edge"] = Relationship(back_populates="edge_type")


class Node(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", ondelete="CASCADE")
    graph_id: UUID = Field(foreign_key="graph.id", ondelete="CASCADE")
    node_type_id: UUID = Field(foreign_key="node_type.id", ondelete="CASCADE")
    key: str # unique identifier within the graph
    display_name: Optional[str] = None
    properties: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})
    source: Optional[str] = None
    source_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB)) # ingestion_run_id, etc.

    client: Client = Relationship(back_populates="nodes")
    graph: Graph = Relationship(back_populates="nodes")
    node_type: NodeType = Relationship(back_populates="nodes")
    
    source_edges: List["Edge"] = Relationship(back_populates="from_node", sa_relationship_kwargs={"foreign_keys": "Edge.from_node_id"})
    target_edges: List["Edge"] = Relationship(back_populates="to_node", sa_relationship_kwargs={"foreign_keys": "Edge.to_node_id"})

    __table_args__ = (
        UniqueConstraint("client_id", "graph_id", "key", name="unique_node_client_graph_key"),
        Index("ix_node_client_node_type", "client_id", "node_type_id"),
    )


class Edge(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", ondelete="CASCADE")
    graph_id: UUID = Field(foreign_key="graph.id", ondelete="CASCADE")
    edge_type_id: UUID = Field(foreign_key="edge_type.id", ondelete="CASCADE")
    from_node_id: UUID = Field(foreign_key="node.id", ondelete="CASCADE")
    to_node_id: UUID = Field(foreign_key="node.id", ondelete="CASCADE")
    properties: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})

    client: Client = Relationship(back_populates="edges")
    graph: Graph = Relationship(back_populates="edges")
    edge_type: EdgeType = Relationship(back_populates="edges")
    from_node: Node = Relationship(back_populates="source_edges", sa_relationship_kwargs={"foreign_keys": "[Edge.from_node_id]"})
    to_node: Node = Relationship(back_populates="target_edges", sa_relationship_kwargs={"foreign_keys": "[Edge.to_node_id]"})

    __table_args__ = (
        Index("ix_edge_client_graph_from", "client_id", "graph_id", "from_node_id"),
        Index("ix_edge_client_graph_to", "client_id", "graph_id", "to_node_id"),
        Index("ix_edge_client_type_from", "client_id", "edge_type_id", "from_node_id"),
    )
