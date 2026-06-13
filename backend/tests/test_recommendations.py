import unittest

from app.services.rag import (
    _skin_type_score,
    is_skin_type_only_message,
    pick_products_for_concerns,
    resolve_recommendation_concerns,
)


class DummyProduct:
    def __init__(
        self,
        product_id: int,
        title: str,
        description: str = "",
        collections: list[str] | None = None,
    ):
        self.id = product_id
        self.title = title
        self.description = description
        self.ingredients = ""
        self.collections = collections or []
        self.price = "$24.00"


class RecommendationLogicTests(unittest.TestCase):
    def test_skin_type_only_message_detection(self) -> None:
        self.assertTrue(is_skin_type_only_message("dry skin"))
        self.assertTrue(is_skin_type_only_message("oily skin"))
        self.assertTrue(is_skin_type_only_message("what about oily skin"))
        self.assertFalse(is_skin_type_only_message("suggest products for dark spots"))

    def test_resolve_concerns_keeps_dark_spots_on_skin_type_follow_up(self) -> None:
        history = [
            {"role": "user", "content": "I want suggestions for dark spots"},
            {
                "role": "assistant",
                "content": "What's your skin type (oily, dry, combination, or sensitive)?",
            },
        ]
        profile = {"concerns": ["hyperpigmentation"], "skin_type": "dry"}
        concerns = resolve_recommendation_concerns("dry skin", profile, history)
        self.assertEqual(concerns[0], "hyperpigmentation")

    def test_skin_type_score_prefers_oily_products_for_oily_skin(self) -> None:
        oily_product = DummyProduct(
            1,
            "Niacinamide Oil Control Gel Moisturizer",
            collections=["Moisturizers", "Oily Skin"],
            description="Lightweight gel for oily and pore-prone skin.",
        )
        dry_product = DummyProduct(
            2,
            "Ceramide Barrier Repair Cream",
            collections=["Moisturizers", "Dry Skin"],
            description="Rich cream for very dry skin.",
        )
        self.assertGreater(_skin_type_score(oily_product, "oily"), _skin_type_score(dry_product, "oily"))
        self.assertGreater(_skin_type_score(dry_product, "dry"), _skin_type_score(oily_product, "dry"))

    def test_pick_products_changes_with_skin_type_for_same_concern(self) -> None:
        products = [
            DummyProduct(
                1,
                "Vitamin C 15% Brightening Serum",
                collections=["Serums", "Brightening"],
                description="Vitamin C serum for dark spots.",
            ),
            DummyProduct(
                2,
                "Oil-Free Hydrating Gel Moisturizer",
                collections=["Moisturizers", "Oily Skin"],
                description="Lightweight gel moisturizer for oily skin.",
            ),
            DummyProduct(
                3,
                "Ceramide Barrier Repair Cream",
                collections=["Moisturizers", "Dry Skin"],
                description="Rich barrier cream for dry skin.",
            ),
            DummyProduct(
                4,
                "Daily SPF 50 Mineral Sunscreen",
                collections=["Sunscreen"],
                description="Mineral sunscreen for sensitive skin.",
            ),
        ]
        concerns = ["hyperpigmentation"]
        oily_picks = pick_products_for_concerns(products, concerns, limit=3, profile={"skin_type": "oily"})
        dry_picks = pick_products_for_concerns(products, concerns, limit=3, profile={"skin_type": "dry"})
        oily_titles = [product.title for product in oily_picks]
        dry_titles = [product.title for product in dry_picks]
        self.assertIn("Vitamin C 15% Brightening Serum", oily_titles)
        self.assertIn("Vitamin C 15% Brightening Serum", dry_titles)
        self.assertIn("Oil-Free Hydrating Gel Moisturizer", oily_titles)
        self.assertIn("Ceramide Barrier Repair Cream", dry_titles)
        self.assertNotEqual(oily_titles, dry_titles)


if __name__ == "__main__":
    unittest.main()
