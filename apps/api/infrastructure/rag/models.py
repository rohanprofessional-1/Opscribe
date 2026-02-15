from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class KnowledgeBaseItem(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(index=True)
    graph_id: UUID = Field(index=True)
    entity_id: UUID = Field(index=True)  # Links to Node.id or Edge.id
    content: str  # The text chunk
    embedding: List[float] = Field(sa_column=Column(Vector(1536)))  # OpenAI embeddings dimensions
    metadata_: Dict[str, Any] = Field(default={}, sa_column=Column("metadata", JSONB))
    created_at: str
    updated_at: str
