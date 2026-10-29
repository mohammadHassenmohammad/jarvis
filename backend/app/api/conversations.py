from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..database.db import (
    get_conversations,
    create_conversation,
    get_conversation,
    delete_conversation,
    clear_all_conversations,
    get_messages
)
from ..services.retrieval_service import retrieval_service

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])

class CreateConvRequest(BaseModel):
    title: Optional[str] = "New Session"

@router.get("")
def list_conversations():
    return {"conversations": get_conversations()}

@router.post("")
def new_conversation(req: CreateConvRequest):
    conv = create_conversation(title=req.title or "New Session")
    return {"conversation": conv}

@router.get("/search")
def search_archived_conversations(
    q: str = Query(..., description="Query terms to search across conversations"),
    limit: int = Query(4, ge=1, le=20)
):
    """
    Search and retrieve relevant conversation excerpts across all past sessions.
    100% local, privacy-preserving.
    """
    snippets = retrieval_service.retrieve_context(query=q, limit=limit)
    return {
        "query": q,
        "count": len(snippets),
        "results": snippets
    }

@router.get("/{conversation_id}")
def get_single_conversation(conversation_id: str):
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = get_messages(conversation_id)
    return {
        "conversation": conv,
        "messages": messages
    }

@router.delete("/{conversation_id}")
def remove_conversation(conversation_id: str):
    success = delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}

@router.delete("")
def clear_all():
    clear_all_conversations()
    return {"success": True, "message": "All conversations cleared"}
