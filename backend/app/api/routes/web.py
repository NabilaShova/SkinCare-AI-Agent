"""Integration endpoints for regular (non-Shopify) websites.

These let a brand without a Shopify store use the same AI agent: register a
website tenant, manage a product catalog manually, and embed the chat widget.
Shopify endpoints and behavior are untouched — this is an additive path that
reuses the shared Store / Product / Document / embedding infrastructure.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.core.security import require_admin
from app.db.models import Product, Store
from app.db.session import get_db
from app.services.rag import index_product_embeddings, remove_product_embeddings

router = APIRouter()

WEB_ACCESS_TOKEN_PLACEHOLDER = "web-no-token"
WEB_SITE_TYPE = "web"


class WebSiteCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website_url: Optional[str] = None
    site_key: Optional[str] = Field(
        default=None,
        description="Unique key for this site. Defaults to the website host or a slug of the name.",
    )


class WebSiteUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    website_url: Optional[str] = None
    is_active: Optional[bool] = None


class WebProductRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    ingredients: Optional[str] = None
    price: Optional[str] = None
    collections: Optional[list[str]] = None
    available: bool = True


class WebProductBulkRequest(BaseModel):
    products: list[WebProductRequest]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "site"


def _derive_site_key(payload: WebSiteCreateRequest) -> str:
    if payload.site_key:
        return payload.site_key.strip().lower()
    if payload.website_url:
        parsed = urlparse(payload.website_url if "//" in payload.website_url else f"//{payload.website_url}")
        host = (parsed.netloc or parsed.path).strip("/").lower()
        host = host.split("/")[0]
        if host:
            return host
    return f"{_slugify(payload.name)}-{uuid.uuid4().hex[:6]}"


def _get_web_store_or_404(store_id: int, db: Session) -> Store:
    store = db.query(Store).filter(Store.id == store_id, Store.is_active.is_(True)).first()
    if not store:
        raise HTTPException(status_code=404, detail="Site not found")
    if store.site_type != WEB_SITE_TYPE:
        raise HTTPException(
            status_code=400,
            detail="This store is a Shopify store. Use the Shopify endpoints for it.",
        )
    return store


def _serialize_site(store: Store) -> dict[str, Any]:
    return {
        "id": store.id,
        "name": store.name,
        "site_key": store.shopify_domain,
        "website_url": store.website_url,
        "site_type": store.site_type,
        "is_active": store.is_active,
        "created_at": store.created_at.isoformat() if store.created_at else None,
    }


def _serialize_product(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "ingredients": product.ingredients,
        "price": product.price,
        "available": product.available,
        "collections": product.collections or [],
    }


@router.post("/sites")
def create_site(
    payload: WebSiteCreateRequest,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    site_key = _derive_site_key(payload)
    existing = db.query(Store).filter(Store.shopify_domain == site_key).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"A store with key '{site_key}' already exists")

    store = Store(
        shopify_domain=site_key,
        access_token=WEB_ACCESS_TOKEN_PLACEHOLDER,
        name=payload.name,
        site_type=WEB_SITE_TYPE,
        website_url=payload.website_url,
        scopes="web-widget",
        is_active=True,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return _serialize_site(store)


@router.get("/sites")
def list_sites(_: None = Depends(require_admin), db: Session = Depends(get_db)) -> dict[str, Any]:
    stores = (
        db.query(Store)
        .filter(Store.site_type == WEB_SITE_TYPE, Store.is_active.is_(True))
        .order_by(Store.id.asc())
        .all()
    )
    return {"items": [_serialize_site(store) for store in stores]}


@router.get("/sites/{store_id}")
def get_site(
    store_id: int,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    store = _get_web_store_or_404(store_id, db)
    return _serialize_site(store)


@router.patch("/sites/{store_id}")
def update_site(
    store_id: int,
    payload: WebSiteUpdateRequest,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    store = _get_web_store_or_404(store_id, db)
    if payload.name is not None:
        store.name = payload.name
    if payload.website_url is not None:
        store.website_url = payload.website_url
    if payload.is_active is not None:
        store.is_active = payload.is_active
    db.add(store)
    db.commit()
    db.refresh(store)
    return _serialize_site(store)


@router.get("/sites/{store_id}/products")
def list_site_products(
    store_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    products = (
        db.query(Product)
        .filter(Product.store_id == store_id)
        .order_by(Product.title.asc())
        .all()
    )
    return {"items": [_serialize_product(product) for product in products]}


def _apply_product_fields(product: Product, payload: WebProductRequest) -> None:
    product.title = payload.title
    product.description = payload.description
    product.ingredients = payload.ingredients
    product.price = payload.price
    product.collections = payload.collections or []
    product.available = payload.available


@router.post("/sites/{store_id}/products")
def create_site_product(
    store_id: int,
    payload: WebProductRequest,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_web_store_or_404(store_id, db)
    product = Product(
        store_id=store_id,
        shopify_product_id=f"web-{uuid.uuid4().hex}",
    )
    _apply_product_fields(product, payload)
    db.add(product)
    db.flush()
    index_product_embeddings(db, store_id)
    db.commit()
    db.refresh(product)
    return _serialize_product(product)


@router.post("/sites/{store_id}/products/bulk")
def create_site_products_bulk(
    store_id: int,
    payload: WebProductBulkRequest,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_web_store_or_404(store_id, db)
    if not payload.products:
        raise HTTPException(status_code=400, detail="No products provided")

    created: list[Product] = []
    for item in payload.products:
        product = Product(store_id=store_id, shopify_product_id=f"web-{uuid.uuid4().hex}")
        _apply_product_fields(product, item)
        db.add(product)
        created.append(product)
    db.flush()
    index_product_embeddings(db, store_id)
    db.commit()
    return {"created": len(created), "items": [_serialize_product(p) for p in created]}


@router.put("/sites/{store_id}/products/{product_id}")
def update_site_product(
    store_id: int,
    product_id: int,
    payload: WebProductRequest,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_web_store_or_404(store_id, db)
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.store_id == store_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _apply_product_fields(product, payload)
    remove_product_embeddings(db, store_id, product_id=product_id)
    db.flush()
    index_product_embeddings(db, store_id)
    db.commit()
    db.refresh(product)
    return _serialize_product(product)


@router.delete("/sites/{store_id}/products/{product_id}")
def delete_site_product(
    store_id: int,
    product_id: int,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_web_store_or_404(store_id, db)
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.store_id == store_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    remove_product_embeddings(db, store_id, product_id=product_id)
    db.delete(product)
    db.commit()
    return {"deleted": True, "product_id": product_id}


@router.get("/site-info")
def get_site_info(
    request: Request,
    store_id: Optional[int] = None,
    site_key: Optional[str] = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Public site lookup for the embedded widget (by id or site key)."""
    enforce_rate_limit(request, namespace="chat", limit_per_minute=settings.RATE_LIMIT_CHAT_PER_MINUTE)
    store: Store | None = None
    if site_key:
        store = (
            db.query(Store)
            .filter(Store.shopify_domain == site_key.strip().lower(), Store.is_active.is_(True))
            .first()
        )
    else:
        resolved_id = store_id or settings.DEMO_STORE_ID
        store = db.query(Store).filter(Store.id == resolved_id, Store.is_active.is_(True)).first()
    if not store:
        raise HTTPException(status_code=404, detail="Site not found")
    return {
        "id": store.id,
        "name": store.name or "Demo Site",
        "site_key": store.shopify_domain,
        "website_url": store.website_url,
        "site_type": store.site_type,
    }
