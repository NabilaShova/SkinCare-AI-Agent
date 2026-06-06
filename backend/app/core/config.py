from typing import Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/support_agent"
    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_APP_URL: Optional[str] = "http://localhost:3000"
    SHOPIFY_SCOPES: str = "read_products,read_orders,write_products,write_orders"
    PGVECTOR_DIMENSION: int = 1536
    DEMO_STORE_ID: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
