from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from ..services.chat_service import chat_service
from ..database.db import get_conversation, create_conversation

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    model: Optional[str] = None

@router.post("")
async def send_chat_message(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conv_id = req.conversation_id
    if not conv_id or not get_conversation(conv_id):
        new_conv = create_conversation(title=req.message[:30])
        conv_id = new_conv["id"]

    return StreamingResponse(
        chat_service.stream_chat(
            conversation_id=conv_id,
            user_message=req.message.strip(),
            model=req.model
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-Id": conv_id
        }
    )
