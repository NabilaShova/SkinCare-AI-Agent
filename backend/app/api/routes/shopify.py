from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.get('/oauth/connect')
def connect_store():
    return {
        'url': f'https://{settings.SHOPIFY_APP_URL}/auth/start'
    }

@router.post('/sync')
def sync_shopify_data(store_id: int, db: Session = Depends(get_db)) -> Any:
    # Placeholder: implement Shopify product, collection, and order sync.
    return {'status': 'sync started', 'store_id': store_id}

@router.get('/products')
def list_products(store_id: int, db: Session = Depends(get_db)) -> Any:
    # Placeholder: return product catalog for storefront retrieval and recommendations.
    return {'items': []}
