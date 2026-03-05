from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from uuid import UUID
from pydantic import BaseModel
from typing import List, Any, Dict, Optional

from apps.api.database import get_session
from apps.api.infrastructure.rag.repo_ingestor import RepoIngestor
from apps.api.infrastructure.rag.retriever import GraphRetriever

router = APIRouter(prefix="/rag", tags=["RAG"])

# --- Models for Requests ---

class RepoIngestRequest(BaseModel):
    tenant_id: UUID
    repo_url: str
    ref: str = "main"

class RagQueryRequest(BaseModel):
    tenant_id: UUID
    query: str
    limit: int = 5

class RagQueryResponse(BaseModel):
    items: List[Dict[str, Any]]

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

@router.post("/query", response_model=RagQueryResponse)
async def query_rag(request: RagQueryRequest, session: Session = Depends(get_session)):
    """
    Queries the vector database for relevant chunks related to a query.
    Returns the raw chunks for now.
    """
    try:
        retriever = GraphRetriever(session)
        results = retriever.retrieve(
            query=request.query, 
            tenant_id=request.tenant_id, 
            limit=request.limit
        )
        
        # Format output
        formatted_results = []
        for item in results:
            formatted_results.append({
                "id": str(item.id),
                "content": item.content,
                "metadata": item.metadata_,
                # Don't return the raw large vector array back to the user usually, just the text
            })
            
        return {"items": formatted_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
