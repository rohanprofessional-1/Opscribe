from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncGenerator

from apps.api.database import get_session
from apps.api.agent.core import get_agent_executor
from apps.api.schemas import ChatRequest, ChatResponse

router = APIRouter(
    prefix="/agent",
    tags=["agent"]
)

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, session: Session = Depends(get_session)):
    """
    Chat with the Opscribe AI Agent.
    """
    try:
        executor = get_agent_executor()
        result = await executor.ainvoke({"input": request.query})
        return ChatResponse(response=result["output"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream", response_model=AsyncGenerator[str, None])
async def chat_stream(request: ChatRequest, session: Session = Depends(get_session)):
    """
    Stream chat responses from the Opscribe AI Agent.
    """
    try:
        executor = get_agent_executor()
        async for chunk in executor.astream({"input": request.query}):
            if "output" in chunk:
                yield chunk["output"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))