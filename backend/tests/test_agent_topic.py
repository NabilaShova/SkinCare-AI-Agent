import unittest

from app.services.agent import (
    _is_face_moisturizer,
    _is_hair_topic,
    _is_non_face_skincare_product,
    _pick_skincare_routine_products,
    _routine_fallback_answer,
    _wants_routine_build,
)
from app.services.rag import detect_concerns


class AgentTopicRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.greeting_history = [
            {
                "role": "assistant",
                "content": (
                    "Hi! I'm the beauty advisor for Glow Beauty Co. "
                    "I can help with skincare and hair care recommendations, ingredient questions, "
                    "shipping, returns, and order status. What would you like help with today?"
                ),
            }
        ]
        self.dry_skin_prompt = (
            "I have dry sensitive skin — suggest a simple morning routine."
        )

    def test_greeting_does_not_force_hair_topic_for_dry_skin_routine(self) -> None:
        self.assertFalse(
            _is_hair_topic(self.dry_skin_prompt, self.greeting_history, {})
        )

    def test_explicit_hair_question_still_routes_to_hair(self) -> None:
        message = "What shampoo helps with hair fall in humid weather?"
        self.assertTrue(_is_hair_topic(message, self.greeting_history, {}))

    def test_detect_concerns_for_dry_sensitive_skin(self) -> None:
        concerns = detect_concerns(self.dry_skin_prompt, {})
        self.assertIn("dryness", concerns)
        self.assertIn("sensitivity", concerns)

    def test_wants_routine_build_for_morning_routine(self) -> None:
        self.assertTrue(
            _wants_routine_build(self.dry_skin_prompt, self.greeting_history, None)
        )


class DummyProduct:
    def __init__(
        self,
        product_id: int,
        title: str,
        description: str = "",
        collections: list[str] | None = None,
        handle: str | None = None,
    ):
        self.id = product_id
        self.title = title
        self.description = description
        self.ingredients = ""
        self.collections = collections or []
        self.price = "$24.00"
        self.handle = handle


class DummyStore:
    def __init__(self, domain: str = "demo-glow-beauty.myshopify.com"):
        self.shopify_domain = domain
        self.site_type = "shopify"
        self.website_url = None


class SkincareRoutineFallbackTests(unittest.TestCase):
    def test_skincare_routine_not_hair_message(self) -> None:
        products = [
            DummyProduct(1, "Gentle Cream Cleanser", collections=["Cleansers", "Sensitive Skin"], handle="gentle-cream-cleanser"),
            DummyProduct(2, "Hydrating Barrier Serum", collections=["Serums", "Dry Skin"], handle="hydrating-barrier-serum"),
            DummyProduct(3, "Rich Ceramide Moisturizer", collections=["Moisturizers", "Dry Skin"], handle="rich-ceramide-moisturizer"),
            DummyProduct(4, "Mineral SPF 50", collections=["Sunscreen", "Sensitive Skin"], handle="mineral-spf-50"),
        ]
        message = "I have dry sensitive skin — suggest a simple morning routine."
        store = DummyStore()
        reply = _routine_fallback_answer(products, {}, message, [], store)
        self.assertNotIn("hair care routine", reply.lower())
        self.assertIn("morning", reply.lower())
        self.assertIn("cleanser", reply.lower())
        self.assertIn("$24.00", reply)
        self.assertIn("](https://demo-glow-beauty.myshopify.com/products/gentle-cream-cleanser)", reply)

    def test_skincare_routine_excludes_product_sets(self) -> None:
        products = [
            DummyProduct(1, "Hydrating Facial Cleanser", collections=["Cleansers"]),
            DummyProduct(2, "Dry Skin Barrier Repair Set", collections=["Serums", "Sets"]),
            DummyProduct(3, "Hyaluronic Hydrating Serum", collections=["Serums", "Dry Skin"]),
            DummyProduct(4, "Ceramide Barrier Repair Cream", collections=["Moisturizers"]),
        ]
        message = "I have dry sensitive skin — suggest a simple morning routine."
        reply = _routine_fallback_answer(products, {}, message, [])
        self.assertNotIn("Barrier Repair Set", reply)
        self.assertIn("Hyaluronic Hydrating Serum", reply)

    def test_skincare_routine_excludes_hand_cream_as_moisturizer(self) -> None:
        products = [
            DummyProduct(1, "Hydrating Facial Cleanser", collections=["Cleansers"]),
            DummyProduct(2, "Hyaluronic Acid Aqua Boost Serum", collections=["Serums", "Dry Skin"]),
            DummyProduct(
                3,
                "Hand Repair Cream with Ceramides",
                collections=["Body Care"],
                description="Rich hand cream for dry and cracked hands.",
            ),
            DummyProduct(
                4,
                "Ceramide Barrier Repair Cream",
                collections=["Moisturizers", "Dry Skin"],
                description="Rich face cream supporting barrier recovery.",
            ),
            DummyProduct(5, "Daily SPF 50 Mineral Sunscreen", collections=["Sunscreen"]),
        ]
        picks = _pick_skincare_routine_products(products, {}, ["dryness"])
        self.assertTrue(_is_non_face_skincare_product(products[2]))
        self.assertFalse(_is_face_moisturizer(products[2]))
        self.assertTrue(_is_face_moisturizer(products[3]))
        self.assertEqual(picks["moisturizer"].title, "Ceramide Barrier Repair Cream")

        message = "I have dry sensitive skin — suggest a simple morning routine."
        reply = _routine_fallback_answer(products, {}, message, [], DummyStore())
        self.assertNotIn("Hand Repair Cream", reply)
        self.assertIn("Ceramide Barrier Repair Cream", reply)

    def test_full_routine_avoids_duplicate_morning_and_night_blocks(self) -> None:
        products = [
            DummyProduct(1, "Hydrating Facial Cleanser", collections=["Cleansers"]),
            DummyProduct(2, "Hyaluronic Acid Aqua Boost Serum", collections=["Serums", "Dry Skin"]),
            DummyProduct(3, "Ceramide Barrier Repair Cream", collections=["Moisturizers", "Dry Skin"]),
            DummyProduct(4, "Daily SPF 50 Mineral Sunscreen", collections=["Sunscreen"]),
        ]
        message = "I have dry skin — build a morning and night routine."
        reply = _routine_fallback_answer(products, {}, message, [], DummyStore())
        self.assertIn("Every day (morning & night):", reply)
        self.assertIn("Morning only:", reply)
        self.assertNotIn("Night:\n1. Cleanser", reply)
        self.assertIn("Night: repeat the cleanser and moisturizer above", reply)
        self.assertEqual(reply.count("Hydrating Facial Cleanser"), 1)
        self.assertEqual(reply.count("Hyaluronic Acid Aqua Boost Serum"), 1)

    def test_full_routine_uses_different_night_serum_when_available(self) -> None:
        products = [
            DummyProduct(1, "Hydrating Facial Cleanser", collections=["Cleansers"]),
            DummyProduct(2, "Hyaluronic Acid Aqua Boost Serum", collections=["Serums", "Dry Skin"]),
            DummyProduct(
                3,
                "Retinol 0.3% Night Renewal Serum",
                collections=["Serums", "Night Care"],
                description="Night retinol serum for renewal.",
            ),
            DummyProduct(4, "Ceramide Barrier Repair Cream", collections=["Moisturizers", "Dry Skin"]),
            DummyProduct(5, "Daily SPF 50 Mineral Sunscreen", collections=["Sunscreen"]),
        ]
        message = "I have dry skin — build a morning and night routine."
        reply = _routine_fallback_answer(products, {}, message, [], DummyStore())
        self.assertIn("Morning only:", reply)
        self.assertIn("Night only:", reply)
        self.assertIn("Hyaluronic Acid Aqua Boost Serum", reply)
        self.assertIn("Retinol 0.3% Night Renewal Serum", reply)


if __name__ == "__main__":
    unittest.main()
