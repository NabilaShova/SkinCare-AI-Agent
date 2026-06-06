from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.db.models import Customer, Order, Product, Store
from app.services.rag import index_product_embeddings
from app.services.shopify_client import ShopifyClient

logger = logging.getLogger(__name__)


def _extract_ingredients(description: str | None, tags: str | None) -> str | None:
    text = " ".join(filter(None, [description or "", tags or ""]))
    if not text:
        return None
    match = re.search(r"ingredients?:\s*([^\n]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _format_price(variants: list[dict[str, Any]]) -> str | None:
    if not variants:
        return None
    price = variants[0].get("price")
    return f"${price}" if price else None


def _upsert_product(db: Session, store_id: int, item: dict[str, Any]) -> None:
    shopify_product_id = str(item["id"])
    product = (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.shopify_product_id == shopify_product_id)
        .first()
    )
    body = item.get("body_html") or ""
    description = re.sub("<[^>]+>", " ", body)
    description = re.sub(r"\s+", " ", description).strip()
    variants = item.get("variants", [])
    available = any(variant.get("inventory_quantity", 0) > 0 for variant in variants) or item.get("status") == "active"

    payload = {
        "title": item.get("title", "Untitled Product"),
        "description": description,
        "ingredients": _extract_ingredients(description, item.get("tags")),
        "collections": [item.get("product_type")] if item.get("product_type") else [],
        "variants": variants,
        "price": _format_price(variants),
        "available": available,
    }

    if product:
        for key, value in payload.items():
            setattr(product, key, value)
        product.updated_at = datetime.utcnow()
    else:
        db.add(Product(store_id=store_id, shopify_product_id=shopify_product_id, **payload))


def _upsert_customer(db: Session, store_id: int, item: dict[str, Any]) -> Customer:
    shopify_customer_id = str(item["id"])
    customer = (
        db.query(Customer)
        .filter(Customer.store_id == store_id, Customer.shopify_customer_id == shopify_customer_id)
        .first()
    )
    if customer:
        customer.email = item.get("email")
        customer.first_name = item.get("first_name")
        customer.last_name = item.get("last_name")
        return customer

    customer = Customer(
        store_id=store_id,
        shopify_customer_id=shopify_customer_id,
        email=item.get("email"),
        first_name=item.get("first_name"),
        last_name=item.get("last_name"),
    )
    db.add(customer)
    db.flush()
    return customer


def _upsert_order(db: Session, store_id: int, item: dict[str, Any], *, sync_customers: bool) -> None:
    shopify_order_id = item.get("name") or f"#{item['id']}"
    order = (
        db.query(Order)
        .filter(Order.store_id == store_id, Order.shopify_order_id == shopify_order_id)
        .first()
    )
    customer = None
    if sync_customers and item.get("customer"):
        customer = _upsert_customer(db, store_id, item["customer"])

    fulfillments = item.get("fulfillments") or []
    tracking_number = None
    if fulfillments:
        tracking_number = fulfillments[0].get("tracking_number")

    payload = {
        "customer_id": customer.id if customer else None,
        "status": item.get("fulfillment_status") or item.get("financial_status") or "open",
        "tracking_number": tracking_number,
        "shipping_address": item.get("shipping_address"),
        "raw_order": item,
    }

    if order:
        for key, value in payload.items():
            setattr(order, key, value)
        order.updated_at = datetime.utcnow()
    else:
        db.add(Order(store_id=store_id, shopify_order_id=shopify_order_id, **payload))


def _sync_resource(label: str, fetcher) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    try:
        return fetcher(), warnings
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            warnings.append(
                f"{label}: access denied (403). Shopify may require Protected Customer Data approval "
                f"or reinstalling the app with updated scopes."
            )
            return [], warnings
        raise
    except Exception as exc:
        warnings.append(f"{label}: sync skipped ({exc})")
        return [], warnings


def sync_store_catalog(db: Session, store: Store) -> dict[str, Any]:
    client = ShopifyClient(store.shopify_domain, store.access_token)
    warnings: list[str] = []

    shop_info = client.get_shop()
    store.name = shop_info.get("name") or store.name

    products, product_warnings = _sync_resource("products", client.get_products)
    warnings.extend(product_warnings)

    customers, customer_warnings = _sync_resource("customers", client.get_customers)
    warnings.extend(customer_warnings)
    customers_allowed = len(customer_warnings) == 0

    orders, order_warnings = _sync_resource("orders", client.get_orders)
    warnings.extend(order_warnings)

    for product in products:
        _upsert_product(db, store.id, product)

    if customers_allowed:
        for customer in customers:
            _upsert_customer(db, store.id, customer)

    for order in orders:
        _upsert_order(db, store.id, order, sync_customers=customers_allowed)

    if products:
        index_product_embeddings(db, store.id)

    store.last_synced_at = datetime.utcnow()
    db.add(store)
    db.commit()

    status = "completed" if products else "partial"
    if not products and warnings:
        status = "failed"

    return {
        "store_id": store.id,
        "shopify_domain": store.shopify_domain,
        "products_synced": len(products),
        "customers_synced": len(customers) if customers_allowed else 0,
        "orders_synced": len(orders),
        "last_synced_at": store.last_synced_at.isoformat() if store.last_synced_at else None,
        "status": status,
        "warnings": warnings,
    }


def sync_store(store_id: int, access_token: str, db: Session) -> dict[str, Any]:
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise ValueError("Store not found")
    store.access_token = access_token
    return sync_store_catalog(db, store)
