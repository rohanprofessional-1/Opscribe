import logging
from uuid import UUID
from sqlmodel import Session
from apps.api.database import engine
from apps.api.ai_infrastructure.rag.ingestor import GraphIngestor

logger = logging.getLogger(__name__)


def re_embed_graph(graph_id: UUID):
    """
    Background task: re-generates all vector embeddings for a graph.
    Creates its own session since BackgroundTasks run after the response
    has already been sent (i.e. outside the request lifecycle).
    """
    logger.info(f"[EmbeddingSync] Starting re-embed for graph {graph_id}")
    try:
        with Session(engine) as session:
            ingestor = GraphIngestor(session)
            ingestor.ingest_graph(graph_id)
        logger.info(f"[EmbeddingSync] Completed re-embed for graph {graph_id}")
    except Exception as e:
        logger.error(f"[EmbeddingSync] Failed to re-embed graph {graph_id}: {e}")
