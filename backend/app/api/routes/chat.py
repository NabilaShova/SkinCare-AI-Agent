from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Message, Store
from app.db.session import get_db
from app.services.agent import generate_agent_reply

router = APIRouter()


class StartChatRequest(BaseModel):
    store_id: Optional[int] = None
    customer_name: Optional[str] = "Guest"


class StartChatResponse(BaseModel):
    conversation_id: int
    store_id: int
    store_name: str
    greeting: str


class ChatMessageRequest(BaseModel):
    conversation_id: int
    content: str


class ChatMessageItem(BaseModel):
    role: str
    content: str


class ChatMessageResponse(BaseModel):
    conversation_id: int
    assistant_reply: ChatMessageItem
    messages: List[ChatMessageItem]
    intent: str
    is_escalated: bool


class ChatConversationResponse(BaseModel):
    conversation_id: int
    store_name: str
    customer_name: Optional[str]
    status: str
    is_escalated: bool
    messages: List[ChatMessageItem]


def _resolve_store(db: Session, store_id: Optional[int]) -> Store:
    resolved_id = store_id or settings.DEMO_STORE_ID
    store = db.query(Store).filter(Store.id == resolved_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.post("/start", response_model=StartChatResponse)
def start_chat(payload: StartChatRequest, db: Session = Depends(get_db)) -> Any:
    store = _resolve_store(db, payload.store_id)
    greeting = (
        f"Hi! I'm the skincare advisor for {store.name}. "
        "I can help with product recommendations, ingredient questions, shipping, returns, and order status. "
        "What would you like help with today?"
    )

    conversation = Conversation(
        store_id=store.id,
        customer_name=payload.customer_name,
        status="open",
        meta={"title": "Customer chat", "source": "chat-widget"},
    )
    db.add(conversation)
    db.flush()

    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=greeting,
            meta={"agent": "greeting"},
        )
    )
    db.commit()
    db.refresh(conversation)

    return StartChatResponse(
        conversation_id=conversation.id,
        store_id=store.id,
        store_name=store.name or "Demo Store",
        greeting=greeting,
    )


@router.get("/{conversation_id}", response_model=ChatConversationResponse)
def get_chat(conversation_id: int, db: Session = Depends(get_db)) -> Any:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    store = db.query(Store).filter(Store.id == conversation.store_id).first()
    messages = [
        ChatMessageItem(role=message.role, content=message.content)
        for message in conversation.messages
    ]
    return ChatConversationResponse(
        conversation_id=conversation.id,
        store_name=(store.name if store else "Demo Store") or "Demo Store",
        customer_name=conversation.customer_name,
        status=conversation.status,
        is_escalated=conversation.is_escalated,
        messages=messages,
    )


@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(payload: ChatMessageRequest, db: Session = Depends(get_db)) -> Any:
    conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.content.strip(),
    )
    db.add(user_message)
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
        meta={
            "intent": agent_result["intent"],
            "sources": agent_result.get("sources", []),
        },
    )
    db.add(assistant_message)
    db.commit()

    messages = [
        ChatMessageItem(role=message.role, content=message.content)
        for message in (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
            .all()
        )
    ]

    db.refresh(conversation)
    return ChatMessageResponse(
        conversation_id=conversation.id,
        assistant_reply=ChatMessageItem(role="assistant", content=agent_result["content"]),
        messages=messages,
        intent=agent_result["intent"],
        is_escalated=conversation.is_escalated,
    )
