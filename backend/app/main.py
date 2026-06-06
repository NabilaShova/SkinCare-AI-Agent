from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.db.init_db import init_database, seed_demo_data
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Shopify Beauty Support Agent API",
    description="FastAPI backend for AI customer support and Shopify store integrations.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
