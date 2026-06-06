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
def list_products(store_id: int = 1, db: Session = Depends(get_db)) -> Any:
    from app.db.models import Product

    products = db.query(Product).filter(Product.store_id == store_id).all()
    return {
        'items': [
            {
                'id': product.id,
                'title': product.title,
                'description': product.description,
                'ingredients': product.ingredients,
                'price': product.price,
                'available': product.available,
                'collections': product.collections,
            }
            for product in products
        ]
    }
