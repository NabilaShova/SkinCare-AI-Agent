from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class ShopifyClient:
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain.replace("https://", "").replace("http://", "").strip("/")
        self.access_token = access_token
        self.api_version = settings.SHOPIFY_API_VERSION
        self.base_url = f"https://{self.shop_domain}/admin/api/{self.api_version}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{self.base_url}{path}", headers=self._headers(), params=params or {})
            response.raise_for_status()
            return response.json()

    def paginate(self, path: str, resource_key: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        query = dict(params or {})
        query.setdefault("limit", 250)

        while True:
            payload = self.get(path, query)
            batch = payload.get(resource_key, [])
            items.extend(batch)
            link_header = None
            # httpx doesn't expose link by default in json helper; use simpler page loop
            if len(batch) < query["limit"]:
                break
            if not batch:
                break
            last_id = batch[-1]["id"]
            query["since_id"] = last_id
            if len(items) > 5000:
                break
        return items

    def get_shop(self) -> dict[str, Any]:
        return self.get("/shop.json").get("shop", {})

    def get_products(self) -> list[dict[str, Any]]:
        return self.paginate("/products.json", "products", {"status": "active"})

    def get_customers(self) -> list[dict[str, Any]]:
        return self.paginate("/customers.json", "customers")

    def get_orders(self) -> list[dict[str, Any]]:
        return self.paginate("/orders.json", "orders", {"status": "any"})
