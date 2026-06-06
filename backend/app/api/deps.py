from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Store
from app.db.session import get_db


def get_store_or_404(store_id: int, db: Session = Depends(get_db)) -> Store:
    store = db.query(Store).filter(Store.id == store_id, Store.is_active.is_(True)).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


def get_conversation_for_store(conversation_id: int, store_id: int, db: Session) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.store_id == store_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def resolve_active_store_id(store_id: int | None) -> int:
    return store_id or settings.DEMO_STORE_ID
