"""
Hybrid RAG + Graph Traversal router.

Dispatches queries through a QueryRouter that classifies intent:
  - "rag"       → vector similarity search → ChatService
  - "traversal" → LangGraph agent with graph traversal tools
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from uuid import UUID
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
import os

from apps.api.database import get_session
from apps.api.ai_infrastructure.rag.repo_ingestor import RepoIngestor
from apps.api.ai_infrastructure.rag.ingestor import GraphIngestor
from apps.api.ai_infrastructure.rag.retriever import GraphRetriever
from apps.api.ai_infrastructure.rag.chat import ChatService
from apps.api.ai_infrastructure.router.query_router import QueryRouter
from apps.api.ai_infrastructure.agent.tools.graph_tools import get_graph_traversal_tools

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

class RagQueryResponse(BaseModel):
    items: List[Dict[str, Any]]
    answer: str
    route: str = "rag"  # "rag" or "traversal"

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
    Hybrid query endpoint.
    Routes to RAG (vector search) or Graph Traversal (agent) based on intent.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured.")

    from langchain_groq import ChatGroq
    # llama-3.1-70b is more reliable for tool use than 3.3-70b on Groq
    llm = ChatGroq(
        temperature=0,
        groq_api_key=api_key,
        model_name="llama-3.1-70b-versatile",
    )

    # ── Step 1: Classify intent ──────────────────────────────────────
    query_router = QueryRouter(llm)
    route = query_router.classify(request.query)

    # ── Step 2: Dispatch ─────────────────────────────────────────────
    if route == "traversal" and request.graph_id:
        return _handle_traversal(request, session, llm)
    else:
        return _handle_rag(request, session)


def _handle_rag(request: RagQueryRequest, session: Session) -> RagQueryResponse:
    """Existing RAG path: vector search → ChatService."""
    try:
        retriever = GraphRetriever(session)
        results = retriever.retrieve(
            query=request.query,
            tenant_id=request.tenant_id,
            limit=request.limit,
            graph_id=request.graph_id,
        )

        formatted_results = []
        context_chunks = []
        for item in results:
            formatted_results.append({
                "id": str(item.id),
                "content": item.content,
                "metadata": item.metadata_,
            })
            context_chunks.append(item.content)

        chat_service = ChatService()
        answer = chat_service.generate_answer(request.query, context_chunks)

        return RagQueryResponse(items=formatted_results, answer=answer, route="rag")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _parse_xml_tool_call(err_str: str) -> Optional[Dict[str, Any]]:
    """
    When Groq emits pseudo-XML like:
        <function=find_node_by_name{"node_name": "API Gateway"}</function>
    it raises a 400 tool_use_failed error with the bad output in 'failed_generation'.
    This parser extracts the tool name and args so we can run the tool directly.
    """
    import re, json
    match = re.search(r'<function=(\w+)(\{.*?\})', err_str, re.DOTALL)
    if not match:
        return None
    tool_name = match.group(1)
    try:
        args = json.loads(match.group(2))
        return {"tool_name": tool_name, "args": args}
    except json.JSONDecodeError:
        return None


def _handle_traversal(
    request: RagQueryRequest,
    session: Session,
    llm,
) -> RagQueryResponse:
    """Graph traversal path: LangGraph agent with graph walk tools."""
    try:
        from langchain.agents import create_agent
        from langchain_core.messages import HumanMessage

        tools = get_graph_traversal_tools(session, request.graph_id)
        tools_by_name = {t.name: t for t in tools}

        system_prompt = (
            "You are the Opscribe Graph Traversal Agent.\n\n"
            "You have access to tools that let you walk the infrastructure architecture graph.\n"
            "Your job is to answer STRUCTURAL questions about the architecture:\n"
            "  - Dependencies (\"what does X depend on?\")\n"
            "  - Impact analysis (\"what breaks if X goes down?\")\n"
            "  - Path finding (\"how does X connect to Y?\")\n"
            "  - Neighbor discovery (\"what are the upstream/downstream services of X?\")\n\n"
            "### PROTOCOL:\n"
            "1. ALWAYS start by using `find_node_by_name` to resolve the component name.\n"
            "2. Then use the appropriate traversal tool based on the question.\n"
            "3. Explain the results clearly using analogies when possible.\n"
            "4. Connect technical findings to business impact.\n\n"
            "### RULES:\n"
            "- You are READ-ONLY. You never modify the graph.\n"
            "- If a node is not found, suggest similar names.\n"
            "- Explain WHY the dependency/impact chain matters, not just WHAT it is.\n\n"
            "### CRITICAL TOOL BEHAVIOR:\n"
            "If you decide to invoke a tool, you MUST output ONLY the tool call. "
            "Do not provide any conversational text, explanations, or thoughts before calling the tool. "
            "Just directly execute the tool."
        )

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
        )

        try:
            result = agent.invoke({"messages": [HumanMessage(content=request.query)]})
            messages = result.get("messages", [])
            answer = "I could not analyze the graph for this question."
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    answer = last_msg.content
            return RagQueryResponse(items=[], answer=answer, route="traversal")

        except Exception as agent_err:
            # ── Groq XML pseudo-format fallback ──────────────────────────
            # When the model emits <function=...> XML instead of a real tool call,
            # Groq returns 400 tool_use_failed. We parse it and run the tool directly.
            err_str = str(agent_err)
            if "tool_use_failed" in err_str or "<function=" in err_str:
                parsed = _parse_xml_tool_call(err_str)
                if parsed:
                    tool = tools_by_name.get(parsed["tool_name"])
                    if tool:
                        tool_result = tool.run(parsed["args"])
                        answer = (
                            f"🔀 **Graph Traversal**\n\n{tool_result}\n\n"
                            f"*The AI used a fallback execution path for `{parsed['tool_name']}`.*"
                        )
                        return RagQueryResponse(items=[], answer=answer, route="traversal")
            raise HTTPException(status_code=500, detail=err_str)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

