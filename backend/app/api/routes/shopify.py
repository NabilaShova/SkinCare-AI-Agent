from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_store_or_404
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.core.security import require_admin
from app.db.models import Product, Store
from app.db.session import get_db
from app.services.shopify_oauth import build_install_url
from app.services.shopify_sync import sync_store_catalog
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/oauth/connect")
def connect_store(shop: str):
    if not settings.SHOPIFY_API_KEY:
        raise HTTPException(status_code=400, detail="Shopify API key is not configured")
    return {"url": build_install_url(shop)}


@router.post("/sync")
def sync_shopify_data(
    store_id: int,
    request: Request,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    enforce_rate_limit(request, namespace="admin", limit_per_minute=settings.RATE_LIMIT_ADMIN_PER_MINUTE)
    store = get_store_or_404(store_id, db)
    try:
        return sync_store_catalog(db, store)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Shopify sync failed: {exc}") from exc


@router.post("/sync-all")
def sync_all_stores(
    request: Request,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    enforce_rate_limit(request, namespace="admin", limit_per_minute=settings.RATE_LIMIT_ADMIN_PER_MINUTE)
    stores = db.query(Store).filter(Store.is_active.is_(True)).all()
    results = []
    for store in stores:
        try:
            results.append(sync_store_catalog(db, store))
        except Exception as exc:
            results.append({"store_id": store.id, "status": "failed", "error": str(exc)})
    return {"results": results, "count": len(results)}


@router.get("/products")
def list_products(store_id: int = 1, db: Session = Depends(get_db)) -> Any:
    products = db.query(Product).filter(Product.store_id == store_id).order_by(Product.title.asc()).all()
    return {
        "items": [
            {
                "id": product.id,
                "title": product.title,
                "description": product.description,
                "ingredients": product.ingredients,
                "price": product.price,
                "available": product.available,
                "collections": product.collections,
            }
            for product in products
        ]
    }


@router.get("/stores")
def list_stores(_: None = Depends(require_admin), db: Session = Depends(get_db)) -> Any:
    stores = db.query(Store).filter(Store.is_active.is_(True)).order_by(Store.id.asc()).all()
    return {
        "items": [
            {
                "id": store.id,
                "name": store.name,
                "shopify_domain": store.shopify_domain,
                "scopes": store.scopes,
                "last_synced_at": store.last_synced_at.isoformat() if store.last_synced_at else None,
            }
            for store in stores
        ]
    }
