from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import ensure_product_indexes, init_database, seed_demo_data
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    db = SessionLocal()
    try:
        if settings.SEED_DEMO_DATA:
            seed_demo_data(db)
        ensure_product_indexes(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Shopify Beauty Support Agent API",
    description="FastAPI backend for AI customer support and Shopify store integrations.",
    version="0.2.0",
    lifespan=lifespan,
)

cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "Shopify Beauty Support Agent",
        "status": "healthy",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
