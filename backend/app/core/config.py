from typing import Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str = ""
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_APP_URL: Optional[str] = "http://localhost:3000"
    SHOPIFY_SCOPES: str = "read_products,read_orders,write_products,write_orders"
    PGVECTOR_DIMENSION: int = 1536

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
