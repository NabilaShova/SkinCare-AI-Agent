from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings


def normalize_shop_domain(shop: str) -> str:
    value = shop.strip().lower()
    value = value.replace("https://", "").replace("http://", "")
    if not value.endswith(".myshopify.com"):
        value = f"{value}.myshopify.com"
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*\.myshopify\.com", value):
        raise ValueError("Invalid Shopify shop domain")
    return value


def verify_hmac(query_params: dict[str, str]) -> bool:
    if not settings.SHOPIFY_API_SECRET:
        return settings.ENVIRONMENT != "production"

    encoded = []
    for key in sorted(query_params.keys()):
        if key in {"hmac", "signature"}:
            continue
        encoded.append(f"{key}={query_params[key]}")
    message = "&".join(encoded).encode("utf-8")
    digest = hmac.new(settings.SHOPIFY_API_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, query_params.get("hmac", ""))


def build_install_url(shop: str, state: str | None = None) -> str:
    shop_domain = normalize_shop_domain(shop)
    redirect_uri = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/auth/callback"
    params = {
        "client_id": settings.SHOPIFY_API_KEY,
        "scope": settings.SHOPIFY_SCOPES,
        "redirect_uri": redirect_uri,
        "state": state or "shopify-oauth",
    }
    return f"https://{shop_domain}/admin/oauth/authorize?{urlencode(params)}"


def exchange_access_token(shop: str, code: str) -> dict[str, Any]:
    shop_domain = normalize_shop_domain(shop)
    url = f"https://{shop_domain}/admin/oauth/access_token"
    payload = {
        "client_id": settings.SHOPIFY_API_KEY,
        "client_secret": settings.SHOPIFY_API_SECRET,
        "code": code,
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
