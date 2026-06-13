import unittest

from app.services.agent import (
    _is_hair_topic,
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
    def __init__(self, product_id: int, title: str, description: str = "", collections: list[str] | None = None):
        self.id = product_id
        self.title = title
        self.description = description
        self.ingredients = ""
        self.collections = collections or []
        self.price = "$24.00"


class SkincareRoutineFallbackTests(unittest.TestCase):
    def test_skincare_routine_not_hair_message(self) -> None:
        products = [
            DummyProduct(1, "Gentle Cream Cleanser", collections=["Cleansers", "Sensitive Skin"]),
            DummyProduct(2, "Hydrating Barrier Serum", collections=["Serums", "Dry Skin"]),
            DummyProduct(3, "Rich Ceramide Moisturizer", collections=["Moisturizers", "Dry Skin"]),
            DummyProduct(4, "Mineral SPF 50", collections=["Sunscreen", "Sensitive Skin"]),
        ]
        message = "I have dry sensitive skin — suggest a simple morning routine."
        reply = _routine_fallback_answer(products, {}, message, [])
        self.assertNotIn("hair care routine", reply.lower())
        self.assertIn("morning", reply.lower())
        self.assertIn("cleanser", reply.lower())


if __name__ == "__main__":
    unittest.main()
