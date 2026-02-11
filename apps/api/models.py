from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship, ARRAY, String
from pydantic import Column
from sqlalchemy.dialects.postgresql import JSONB

class ArchitectureGraph(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: Optional[str] = None
    nodes: List["Node"] = Relationship(back_populates="graph")
    edges: List["Edge"] = Relationship(back_populates="graph")

class Node(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    graph_id: UUID = Field(foreign_key="architecturegraph.id")
    type: str  # e.g., "service", "database", "queue"
    label: str
    data: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    position_x: float
    position_y: float
    
    graph: Optional[ArchitectureGraph] = Relationship(back_populates="nodes")
    source_edges: List["Edge"] = Relationship(back_populates="source_node", sa_relationship_kwargs={"foreign_keys": "Edge.source_id"})
    target_edges: List["Edge"] = Relationship(back_populates="target_node", sa_relationship_kwargs={"foreign_keys": "Edge.target_id"})

class Edge(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    graph_id: UUID = Field(foreign_key="architecturegraph.id")
    source_id: UUID = Field(foreign_key="node.id")
    target_id: UUID = Field(foreign_key="node.id")
    type: str = "default"
    data: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))

    graph: Optional[ArchitectureGraph] = Relationship(back_populates="edges")
    source_node: Optional[Node] = Relationship(back_populates="source_edges", sa_relationship_kwargs={"foreign_keys": "Edge.source_id"})
    target_node: Optional[Node] = Relationship(back_populates="target_edges", sa_relationship_kwargs={"foreign_keys": "Edge.target_id"})
