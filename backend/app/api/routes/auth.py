from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_admin_token, require_admin, verify_admin_api_key
from app.db.models import Store
from app.db.session import get_db
from app.services.shopify_oauth import build_install_url, exchange_access_token, normalize_shop_domain, verify_hmac
from app.services.shopify_sync import sync_store_catalog

router = APIRouter()


class AdminLoginRequest(BaseModel):
    api_key: str
    store_id: int = 1


@router.get("/start")
def start_shopify_oauth(shop: str = Query(..., description="Shopify shop domain")):
    if not settings.SHOPIFY_API_KEY or not settings.SHOPIFY_API_SECRET:
        raise HTTPException(status_code=400, detail="Shopify API credentials are not configured")

    install_url = build_install_url(shop)
    return RedirectResponse(url=install_url)


@router.get("/callback")
def oauth_callback(request: Request, db: Session = Depends(get_db)):
    params = {key: value for key, value in request.query_params.items()}
    shop = params.get("shop")
    code = params.get("code")

    if not shop or not code:
        raise HTTPException(status_code=400, detail="Missing shop or authorization code")
    if not verify_hmac(params):
        raise HTTPException(status_code=400, detail="Invalid Shopify HMAC")

    shop_domain = normalize_shop_domain(shop)
    token_payload = exchange_access_token(shop_domain, code)
    access_token = token_payload.get("access_token")
    scopes = token_payload.get("scope", settings.SHOPIFY_SCOPES)

    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to obtain Shopify access token")

    store = db.query(Store).filter(Store.shopify_domain == shop_domain).first()
    if store:
        store.access_token = access_token
        store.scopes = scopes
        store.is_active = True
    else:
        store = Store(
            shopify_domain=shop_domain,
            access_token=access_token,
            name=shop_domain,
            scopes=scopes,
            is_active=True,
        )
        db.add(store)

    db.commit()
    db.refresh(store)

    try:
        sync_store_catalog(db, store)
    except Exception:
        pass

    redirect_url = f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/dashboard/settings?connected=1&store_id={store.id}"
    return RedirectResponse(url=redirect_url)


@router.post("/admin/login")
def admin_login(payload: AdminLoginRequest) -> dict[str, Any]:
    verify_admin_api_key(payload.api_key)
    token = create_admin_token(payload.store_id)
    return {"access_token": token, "token_type": "bearer", "store_id": payload.store_id}


@router.get("/status")
def auth_status(_: None = Depends(require_admin), db: Session = Depends(get_db)) -> dict[str, Any]:
    stores = db.query(Store).filter(Store.is_active.is_(True)).all()
    return {
        "stores": [
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
