# app/api/v1/chat.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.models.schemas import ChatMessage
from app.services.rag import query_rag, chat
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/query")
async def query_documents(
    question: str,
    k: int = Query(4, ge=1, le=10, description="Number of documents to retrieve"),
    query_type: str = Query("similarity", description="similarity or mmr"),
    include_sources: bool = Query(True)
):
    """
    Query the document knowledge base.
    Single question without conversation history.
    """
    result = await query_rag(
        question=question,
        k=k,
        query_type=query_type,
        include_sources=include_sources
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Query failed"))
    
    return result

@router.post("/conversation")
async def chat_with_history(
    message: str,
    conversation_id: Optional[str] = None,
    k: int = Query(4, ge=1, le=10)
):
    """
    Chat with conversation history.
    Maintains context across messages.
    """
    result = await chat(
        message=message,
        conversation_id=conversation_id,
        k=k
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Chat failed"))
    
    return result

@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history."""
    from app.services.rag import conversations
    
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": conversations[conversation_id]
    }

@router.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history."""
    from app.services.rag import conversations
    
    if conversation_id in conversations:
        del conversations[conversation_id]
    
    return {"message": "Conversation cleared"}