from fastapi import APIRouter
from app.api.routes import analytics, auth, chat, conversations, knowledge, shopify

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(shopify.router, prefix="/shopify", tags=["shopify"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
