import unittest

from app.services.product_links import build_product_url, format_product_markdown_link, slugify_product_handle


class DummyProduct:
    def __init__(self, title: str, handle: str | None = None, price: str = "$18.00"):
        self.title = title
        self.handle = handle
        self.price = price


class DummyStore:
    def __init__(self, domain: str = "demo-glow-beauty.myshopify.com", site_type: str = "shopify"):
        self.shopify_domain = domain
        self.site_type = site_type
        self.website_url = None


class ProductLinkTests(unittest.TestCase):
    def test_slugify_product_handle(self) -> None:
        self.assertEqual(slugify_product_handle("Gentle Foaming Cleanser"), "gentle-foaming-cleanser")

    def test_build_product_url_with_handle(self) -> None:
        store = DummyStore()
        product = DummyProduct("Gentle Foaming Cleanser", handle="gentle-foaming-cleanser")
        self.assertEqual(
            build_product_url(store, product),
            "https://demo-glow-beauty.myshopify.com/products/gentle-foaming-cleanser",
        )

    def test_build_product_url_falls_back_to_title_slug(self) -> None:
        store = DummyStore()
        product = DummyProduct("Daily SPF 50 Mineral Sunscreen")
        self.assertEqual(
            build_product_url(store, product),
            "https://demo-glow-beauty.myshopify.com/products/daily-spf-50-mineral-sunscreen",
        )

    def test_format_product_markdown_link(self) -> None:
        store = DummyStore()
        product = DummyProduct("Gentle Foaming Cleanser", handle="gentle-foaming-cleanser", price="$18.00")
        self.assertEqual(
            format_product_markdown_link(store, product),
            "[Gentle Foaming Cleanser ($18.00)](https://demo-glow-beauty.myshopify.com/products/gentle-foaming-cleanser)",
        )


if __name__ == "__main__":
    unittest.main()
