from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, HttpUrl

class StoreBase(BaseModel):
    shopify_domain: str
    name: Optional[str]

class StoreCreate(StoreBase):
    access_token: str

class StoreRead(StoreBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ProductRead(BaseModel):
    id: int
    shopify_product_id: str
    title: str
    description: Optional[str]
    ingredients: Optional[str]
    collections: Optional[Any]
    variants: Optional[Any]
    price: Optional[str]
    available: bool

    class Config:
        orm_mode = True

class ConversationCreate(BaseModel):
    store_id: int
    customer_name: Optional[str]
    metadata: Optional[Any]

class ConversationRead(BaseModel):
    id: int
    store_id: int
    customer_name: Optional[str]
    status: str
    is_escalated: bool
    metadata: Optional[Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class MessageCreate(BaseModel):
    conversation_id: int
    role: str
    content: str
    metadata: Optional[Any]

class MessageRead(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    metadata: Optional[Any]
    created_at: datetime

    class Config:
        orm_mode = True
