from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Conversation, Escalation, Message
from app.db.session import get_db
from app.services.agent import generate_agent_reply

router = APIRouter()


class ConversationSummary(BaseModel):
    id: int
    title: str
    customer: str
    preview: str
    last_activity: str
    status: str
    is_escalated: bool


class MessagePayload(BaseModel):
    conversation_id: int
    role: str
    content: str


class MessageItem(BaseModel):
    role: str
    content: str


class ConversationDetail(BaseModel):
    id: int
    title: str
    customer: str
    status: str
    is_escalated: bool
    messages: List[MessageItem]


def _format_last_activity(timestamp: Optional[datetime]) -> str:
    if not timestamp:
        return "just now"
    now = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    delta = now - timestamp
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _conversation_title(conversation: Conversation) -> str:
    meta = conversation.meta or {}
    if meta.get("title"):
        return meta["title"]
    first_user_message = next((message for message in conversation.messages if message.role == "user"), None)
    if first_user_message:
        return first_user_message.content[:48]
    return f"Conversation #{conversation.id}"


@router.get("/", response_model=List[ConversationSummary])
def list_conversations(store_id: Optional[int] = None, db: Session = Depends(get_db)) -> Any:
    query = db.query(Conversation).order_by(Conversation.updated_at.desc())
    if store_id:
        query = query.filter(Conversation.store_id == store_id)

    conversations = query.all()
    summaries = []
    for conversation in conversations:
        last_message = conversation.messages[-1] if conversation.messages else None
        preview = last_message.content[:80] if last_message else "No messages yet"
        summaries.append(
            ConversationSummary(
                id=conversation.id,
                title=_conversation_title(conversation),
                customer=conversation.customer_name or "Guest",
                preview=preview,
                last_activity=_format_last_activity(conversation.updated_at),
                status=conversation.status,
                is_escalated=conversation.is_escalated,
            )
        )
    return summaries


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)) -> Any:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetail(
        id=conversation.id,
        title=_conversation_title(conversation),
        customer=conversation.customer_name or "Guest",
        status=conversation.status,
        is_escalated=conversation.is_escalated,
        messages=[
            MessageItem(role=message.role, content=message.content) for message in conversation.messages
        ],
    )


@router.post("/message")
def send_message(payload: MessagePayload, db: Session = Depends(get_db)) -> Any:
    conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if payload.role != "user":
        raise HTTPException(status_code=400, detail="Only user messages can be sent from the dashboard")

    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=payload.content.strip(),
        )
    )
    db.flush()

    agent_result = generate_agent_reply(
        db,
        store_id=conversation.store_id,
        conversation_id=conversation.id,
        user_message=payload.content.strip(),
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=agent_result["content"],
        meta={"intent": agent_result["intent"], "sources": agent_result.get("sources", [])},
    )
    db.add(assistant_message)
    db.commit()

    messages = [
        {"role": message.role, "content": message.content}
        for message in (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
            .all()
        )
    ]

    return {
        "conversation_id": conversation.id,
        "assistant_reply": {"role": "assistant", "content": agent_result["content"]},
        "messages": messages,
        "intent": agent_result["intent"],
    }


@router.post("/escalate")
def escalate_conversation(conversation_id: int, reason: str, db: Session = Depends(get_db)) -> Any:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.status = "escalated"
    conversation.is_escalated = True
    db.add(
        Escalation(
            conversation_id=conversation.id,
            reason=reason,
            status="pending",
        )
    )
    db.commit()
    return {"conversation_id": conversation_id, "escalated": True, "reason": reason}
