from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from uuid import UUID
from pydantic import BaseModel
from typing import List, Any, Dict, Optional

from apps.api.database import get_session
from apps.api.ai_infrastructure.rag.repo_ingestor import RepoIngestor
from apps.api.ai_infrastructure.rag.ingestor import GraphIngestor
from apps.api.ai_infrastructure.rag.retriever import GraphRetriever

router = APIRouter(prefix="/rag", tags=["RAG"])

# --- Models for Requests ---

class RepoIngestRequest(BaseModel):
    tenant_id: UUID
    repo_url: str
    ref: str = "main"

class GraphIngestRequest(BaseModel):
    graph_id: UUID

class RagQueryRequest(BaseModel):
    tenant_id: UUID
    graph_id: Optional[UUID] = None
    query: str
    limit: int = 5

from apps.api.ai_infrastructure.rag.chat import ChatService

class RagQueryResponse(BaseModel):
    items: List[Dict[str, Any]]
    answer: str

# --- Endpoints ---

@router.post("/ingest/repo")
async def ingest_repo(request: RepoIngestRequest, session: Session = Depends(get_session)):
    """
    Clones a repository, chunks it, embeds it, and saves it into the vector database.
    """
    try:
        ingestor = RepoIngestor(session)
        chunks_created = ingestor.ingest_repo(
            repo_url=request.repo_url, 
            tenant_id=request.tenant_id, 
            ref=request.ref
        )
        return {"status": "success", "chunks_ingested": chunks_created, "repo_url": request.repo_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/graph")
async def ingest_graph(request: GraphIngestRequest, session: Session = Depends(get_session)):
    """
    Ingests an existing architecture graph from the database into the vector database.
    """
    try:
        ingestor = GraphIngestor(session)
        ingestor.ingest_graph(graph_id=request.graph_id)
        return {"status": "success", "graph_id": request.graph_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=RagQueryResponse)
async def query_rag(request: RagQueryRequest, session: Session = Depends(get_session)):
    """
    Queries the vector database for relevant chunks and generates an answer using Groq.
    """
    try:
        # 1. Retrieve
        retriever = GraphRetriever(session)
        results = retriever.retrieve(
            query=request.query, 
            tenant_id=request.tenant_id, 
            limit=request.limit,
            graph_id=request.graph_id
        )
        
        # 2. Format Chunks
        formatted_results = []
        context_chunks = []
        for item in results:
            formatted_results.append({
                "id": str(item.id),
                "content": item.content,
                "metadata": item.metadata_,
            })
            context_chunks.append(item.content)
            
        # 3. Generate Answer
        chat_service = ChatService()
        answer = chat_service.generate_answer(request.query, context_chunks)

        return {"items": formatted_results, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
