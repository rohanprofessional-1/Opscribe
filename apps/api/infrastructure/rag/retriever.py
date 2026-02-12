from uuid import UUID
from typing import List, Tuple
from sqlmodel import Session, select
from pgvector.sqlalchemy import Vector
from sqlalchemy import text

from apps.api.infrastructure.rag.models import KnowledgeBaseItem
from apps.api.infrastructure.rag.embeddings import EmbeddingService

class GraphRetriever:
    def __init__(self, session: Session):
        self.session = session
        self.embedding_service = EmbeddingService()

    def retrieve(self, query: str, tenant_id: UUID, limit: int = 5) -> List[KnowledgeBaseItem]:
        # 1. Generate Query Embedding
        query_embedding = self.embedding_service.generate_embedding(query)

        # 2. Vector Search (Cosine Similarity)
        # Using pgvector's <-> operator for L2 distance (or cosine distance for normalized vectors)
        # We need to cast the embedding list to text for SQL if using raw SQL, 
        # but SQLModel/SQLAlchemy + pgvector should handle list -> vector conversion.
        
        # Note: pgvector creates a vector type. 
        # For cosine distance, we typically normalize vectors or use cosine operator <=> 
        # But 'OPENAI' embeddings are usually normalized, so L2/Euclidean is fine for ranking, or <=> for cosine distance.
        # Let's use cosine distance operator <=> 
        
        stmt = select(KnowledgeBaseItem).where(
            KnowledgeBaseItem.tenant_id == tenant_id
        ).order_by(
            KnowledgeBaseItem.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        results = self.session.exec(stmt).all()
        return results
