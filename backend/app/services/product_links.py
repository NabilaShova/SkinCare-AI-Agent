from __future__ import annotations

import re

from app.db.models import Product, Store


def slugify_product_handle(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "product"


def build_product_url(store: Store | None, product: Product) -> str | None:
    handle = (getattr(product, "handle", None) or "").strip() or slugify_product_handle(product.title)
    if not store:
        return None

    if store.site_type == "web":
        base = (store.website_url or "").strip().rstrip("/")
        if not base:
            return None
        return f"{base}/products/{handle}"

    domain = (store.shopify_domain or "").strip().lower()
    if not domain:
        return None
    if domain.startswith("http://") or domain.startswith("https://"):
        base = domain.rstrip("/")
    else:
        base = f"https://{domain.rstrip('/')}"
    return f"{base}/products/{handle}"


def format_product_markdown_link(
    store: Store | None,
    product: Product,
    *,
    with_price: bool = True,
) -> str:
    price = (product.price or "").strip()
    if with_price and price:
        label = f"{product.title} ({price})"
    else:
        label = product.title

    url = build_product_url(store, product)
    if url:
        return f"[{label}]({url})"
    return label
