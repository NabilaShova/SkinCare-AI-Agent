from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Conversation, Document, EmbeddingRecord, Message
from app.services.rag import chunk_text, generate_embeddings


def _learned_filename(message_id: int) -> str:
    return f"chat-learned-message-{message_id}.txt"


def _build_learned_text(
    question: str,
    answer: str,
    *,
    intent: str | None = None,
    correction: str | None = None,
) -> str:
    final_answer = correction.strip() if correction and correction.strip() else answer.strip()
    intent_label = intent or "general"
    return (
        f"Learned Customer FAQ\n"
        f"Intent: {intent_label}\n\n"
        f"Customer question:\n{question.strip()}\n\n"
        f"Recommended answer:\n{final_answer}\n"
    )


def _preceding_user_message(db: Session, assistant_message: Message) -> Message | None:
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == assistant_message.conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    for index, message in enumerate(messages):
        if message.id != assistant_message.id:
            continue
        if index == 0:
            return None
        previous = messages[index - 1]
        return previous if previous.role == "user" else None
    return None


def _already_learned(db: Session, store_id: int, message_id: int) -> bool:
    filename = _learned_filename(message_id)
    existing = (
        db.query(Document)
        .filter(Document.store_id == store_id, Document.filename == filename)
        .first()
    )
    return existing is not None


def promote_message_to_knowledge(
    db: Session,
    *,
    assistant_message: Message,
    store_id: int,
    correction: str | None = None,
) -> dict[str, Any] | None:
    if assistant_message.role != "assistant":
        return None

    meta = assistant_message.meta or {}
    if meta.get("agent") == "greeting":
        return None

    if _already_learned(db, store_id, assistant_message.id):
        return {"status": "already_learned", "message_id": assistant_message.id}

    user_message = _preceding_user_message(db, assistant_message)
    if not user_message:
        return None

    intent = meta.get("intent")
    raw_text = _build_learned_text(
        user_message.content,
        assistant_message.content,
        intent=intent,
        correction=correction,
    )
    document = Document(
        store_id=store_id,
        filename=_learned_filename(assistant_message.id),
        content_type="text/plain",
        status="processing",
        raw_text=raw_text,
    )
    db.add(document)
    db.flush()

    chunks = chunk_text(raw_text)
    embeddings = generate_embeddings(chunks)
    for index, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        db.add(
            EmbeddingRecord(
                store_id=store_id,
                document_id=document.id,
                chunk_text=chunk,
                vector=vector,
                meta={
                    "source": document.filename,
                    "chunk_index": index,
                    "type": "chat-learned",
                    "message_id": assistant_message.id,
                    "intent": intent,
                },
            )
        )

    document.status = "processed"
    assistant_message.meta = {
        **meta,
        "learned": True,
        "learned_document_id": document.id,
    }
    db.add(assistant_message)

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == assistant_message.conversation_id)
        .first()
    )
    if conversation:
        conversation_meta = conversation.meta or {}
        conversation_meta["learned_exchanges"] = int(conversation_meta.get("learned_exchanges", 0)) + 1
        conversation.meta = conversation_meta
        db.add(conversation)

    return {
        "status": "learned",
        "message_id": assistant_message.id,
        "document_id": document.id,
        "chunks_indexed": len(chunks),
    }


def record_chat_feedback(
    db: Session,
    *,
    message_id: int,
    helpful: bool,
    correction: str | None = None,
    auto_learn: bool = True,
) -> dict[str, Any]:
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise ValueError("Message not found")
    if message.role != "assistant":
        raise ValueError("Feedback is only supported on assistant messages")

    conversation = db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
    if not conversation:
        raise ValueError("Conversation not found")

    feedback_meta = {
        "helpful": helpful,
        "correction": correction,
    }
    message.meta = {**(message.meta or {}), "feedback": feedback_meta}
    db.add(message)

    result: dict[str, Any] = {
        "message_id": message_id,
        "helpful": helpful,
        "learned": False,
    }

    if helpful and auto_learn:
        learned = promote_message_to_knowledge(
            db,
            assistant_message=message,
            store_id=conversation.store_id,
            correction=correction,
        )
        if learned and learned.get("status") == "learned":
            result["learned"] = True
            result["document_id"] = learned.get("document_id")
            result["chunks_indexed"] = learned.get("chunks_indexed")

    db.commit()
    return result
