from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/support_agent"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    FRONTEND_PUBLIC_URL: str = "http://localhost:3000"

    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_INTENT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_TEMPERATURE: float = 0.3

    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_APP_URL: Optional[str] = "http://localhost:3000"
    SHOPIFY_API_VERSION: str = "2024-10"
    SHOPIFY_SCOPES: str = "read_products,read_orders,read_content"

    ADMIN_API_KEY: str = "dev-admin-key-change-me"
    JWT_SECRET: str = "dev-jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    PGVECTOR_DIMENSION: int = 1536
    DEMO_STORE_ID: int = 1
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.12
    PRODUCT_TOP_K: int = 5
    CHAT_HISTORY_LIMIT: int = 12

    RATE_LIMIT_CHAT_PER_MINUTE: int = 30
    RATE_LIMIT_ADMIN_PER_MINUTE: int = 120

    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"
    SEED_DEMO_DATA: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
