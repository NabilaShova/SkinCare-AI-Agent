from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Message, Order, Product
from app.services.rag import (
    CONCERN_SIGNALS,
    build_retrieval_query,
    concern_label,
    detect_concerns,
    detect_policy_topic,
    detect_requested_product_types,
    effective_profile_for_retrieval,
    filter_ingredient_hits,
    filter_policy_hits,
    filter_products_for_query,
    format_knowledge_context,
    pick_products_for_concerns,
    search_knowledge,
    search_products,
)

Intent = Literal[
    "product_recommendation",
    "ingredient_question",
    "order_support",
    "policy_faq",
    "medical_safety",
    "escalation",
    "general",
]


class AgentState(TypedDict):
    store_id: int
    conversation_id: int
    user_message: str
    intent: str
    context: dict[str, Any]
    response: str
    should_escalate: bool
    sources: list[str]


MEDICAL_PATTERNS = [
    r"\binfection\b",
    r"\ballergic reaction\b",
    r"\bdermatitis\b",
    r"\bprescribe\b",
    r"\bdiagnos",
    r"\bsevere acne\b",
    r"\brash\b",
    r"\bswelling\b",
    r"\bpsoriasis\b",
    r"\beczema\b",
    r"\bhives\b",
]

ESCALATION_PATTERNS = [
    r"\brefund dispute\b",
    r"\bchargeback\b",
    r"\bnot happy\b",
    r"\bangry\b",
    r"\bspeak to (a )?human\b",
    r"\bmanager\b",
    r"\bterrible service\b",
    r"\bunacceptable\b",
    r"\blawyer\b",
]

INTENT_TEMPERATURES = {
    "product_recommendation": 0.45,
    "ingredient_question": 0.15,
    "order_support": 0.1,
    "policy_faq": 0.1,
    "medical_safety": 0.0,
    "escalation": 0.2,
    "general": 0.3,
}

PROFILE_CONCERNS = [
    "acne",
    "hyperpigmentation",
    "dark spots",
    "fine lines",
    "wrinkles",
    "redness",
    "dehydration",
    "uneven skin tone",
    "enlarged pores",
]

SKIN_TYPES = ["oily", "dry", "combination", "sensitive", "normal"]

CUSTOMER_REPLY_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bfrom your catalog\b", "from our store"),
    (r"\bin your catalog\b", "in our store"),
    (r"\byour synced catalog\b", "our store"),
    (r"\byour store catalog\b", "our store"),
    (r"\bproducts from your store\b", "products we carry"),
    (r"\bin your store include\b", "we carry"),
    (r"\bin your store\b", "in our store"),
    (r"\byour catalog\b", "our store"),
    (r"\bcatalog options\b", "options from our store"),
    (r"\bthe current catalog\b", "our store"),
    (r"\bcurrent store catalog\b", "our store"),
)


def _polish_customer_reply(text: str) -> str:
    polished = text
    for pattern, replacement in CUSTOMER_REPLY_REPLACEMENTS:
        polished = re.sub(pattern, replacement, polished, flags=re.IGNORECASE)
    return polished


AFFIRMATIVE_REPLIES = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "ok",
    "okay",
    "please",
    "yes please",
    "sounds good",
    "do it",
    "go ahead",
    "that works",
}

PRODUCT_BROWSE_TERMS = [
    "show me",
    "options",
    "sunscreen",
    "spf",
    "moisturizer",
    "serum",
    "cleanser",
    "toner",
    "mask",
    "affordable",
    "reasonable",
    "budget",
    "under",
    "recommend",
    "suggest",
    "help me find",
    "looking for",
    "hydrating",
]


def _is_affirmative(message: str) -> bool:
    lowered = message.lower().strip("!.? ")
    return lowered in AFFIRMATIVE_REPLIES or lowered.startswith("yes ")


def _last_assistant_offered_routine(history: list[dict[str, str]]) -> bool:
    for item in reversed(history):
        if item["role"] == "assistant":
            lowered = item["content"].lower()
            return "routine" in lowered or "morning" in lowered or "night" in lowered
    return False


def _last_assistant_offered_products(history: list[dict[str, str]]) -> bool:
    for item in reversed(history):
        if item["role"] == "assistant":
            lowered = item["content"].lower()
            return any(
                phrase in lowered
                for phrase in (
                    "suggest suitable products",
                    "suitable products if you'd like",
                    "products from our store",
                    "products from your catalog",
                    "from our store if you'd like",
                    "recommend products",
                )
            )
    return False


INGREDIENT_KEYWORDS: dict[str, list[str]] = {
    "retinol": ["retinol", "retinoid", "retinal"],
    "salicylic acid": ["salicylic", "bha"],
    "niacinamide": ["niacinamide"],
    "vitamin c": ["vitamin c", "ascorbic", "l-ascorbic"],
    "benzoyl peroxide": ["benzoyl"],
    "glycolic acid": ["glycolic"],
    "lactic acid": ["lactic"],
    "azelaic acid": ["azelaic"],
    "hyaluronic acid": ["hyaluronic"],
}

INGREDIENT_PAIR_ANSWERS: dict[frozenset[str], str] = {
    frozenset({"retinol", "salicylic acid"}): (
        "Yes — retinol and salicylic acid (BHA) can be part of the same skincare plan, but avoid using both on the "
        "same night when you're starting out. Alternate evenings (BHA one night, retinol the next), moisturize after "
        "each, and wear SPF every morning. If your skin is sensitive, keep them on separate nights until tolerated."
    ),
    frozenset({"niacinamide", "vitamin c"}): (
        "Yes — niacinamide and vitamin C can be used together in many routines. For sensitive skin, use vitamin C in "
        "the morning and niacinamide at night. For tolerant skin, layer by texture (thinnest first)."
    ),
    frozenset({"retinol", "benzoyl peroxide"}): (
        "Use caution — benzoyl peroxide and retinol can irritate skin when combined. Alternate nights when starting, "
        "and never skip morning sunscreen."
    ),
    frozenset({"retinol", "glycolic acid"}): (
        "Do not use retinol and glycolic acid (AHA) on the same night when beginning. Alternate evenings and moisturize "
        "after each active."
    ),
    frozenset({"retinol", "lactic acid"}): (
        "Do not use retinol and lactic acid (AHA) on the same night when beginning. Alternate evenings and moisturize "
        "after each active."
    ),
}


def _recent_substantive_user_message(history: list[dict[str, str]]) -> str:
    for item in reversed(history):
        if item["role"] != "user":
            continue
        content = item["content"].strip()
        if _is_affirmative(content):
            continue
        if len(content.split()) <= 2:
            continue
        return content
    return ""


def _extract_mentioned_ingredients(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for name, terms in INGREDIENT_KEYWORDS.items():
        if any(term in lowered for term in terms):
            found.append(name)
    return found


def _is_ingredient_product_followup(
    message: str,
    history: list[dict[str, str]],
    last_intent: str | None,
) -> bool:
    return _is_affirmative(message) and last_intent == "ingredient_question" and _last_assistant_offered_products(
        history
    )


def _ingredient_terms(ingredients: list[str]) -> list[str]:
    terms: list[str] = []
    for ingredient in ingredients:
        terms.extend(INGREDIENT_KEYWORDS.get(ingredient, [ingredient]))
    return terms


def _pick_products_for_ingredients(
    products: list[Product],
    ingredients: list[str],
    limit: int = 3,
) -> list[Product]:
    if not products:
        return []

    ranked = sorted(
        products,
        key=lambda product: sum(
            1 for term in _ingredient_terms(ingredients) if term in _product_haystack(product)
        ),
        reverse=True,
    )
    picks: list[Product] = []
    seen_ids: set[int] = set()

    for ingredient in ingredients:
        terms = INGREDIENT_KEYWORDS.get(ingredient, [ingredient])
        for product in ranked:
            if product.id in seen_ids:
                continue
            if any(term in _product_haystack(product) for term in terms):
                picks.append(product)
                seen_ids.add(product.id)
                break

    for product in ranked:
        if product.id in seen_ids:
            continue
        picks.append(product)
        seen_ids.add(product.id)
        if len(picks) >= limit:
            break

    return picks[:limit]


def _classify_intent_rules(message: str) -> Intent:
    lowered = message.lower()

    if any(re.search(pattern, lowered) for pattern in MEDICAL_PATTERNS):
        return "medical_safety"
    if any(re.search(pattern, lowered) for pattern in ESCALATION_PATTERNS):
        return "escalation"
    if any(term in lowered for term in ["where is my order", "tracking", "shipped", "order status", "order #", "order number"]):
        return "order_support"
    if any(term in lowered for term in ["ship", "shipping", "delivery", "international", "return", "refund", "policy"]):
        return "policy_faq"
    if any(term in lowered for term in ["niacinamide", "vitamin c", "retinol", "salicylic", "ingredient", "can i use", "compatible", "mix", "layer"]):
        return "ingredient_question"
    if any(
        term in lowered
        for term in [
            "recommend",
            "routine",
            "best for",
            "which product",
            "help me choose",
            "skin type",
            "what should i buy",
            "complete routine",
            "morning routine",
            "night routine",
        ]
    ) or any(term in lowered for term in SKIN_TYPES + PROFILE_CONCERNS):
        return "product_recommendation"
    if any(term in lowered for term in PRODUCT_BROWSE_TERMS):
        return "product_recommendation"
    return "general"


def _classify_intent_llm(message: str, history: list[dict[str, str]], profile: dict[str, Any]) -> Intent | None:
    if not settings.OPENAI_API_KEY:
        return None

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_INTENT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        recent = "\n".join(f"{item['role']}: {item['content']}" for item in history[-4:])
        prompt = (
            "Classify the latest customer message into exactly one intent:\n"
            "product_recommendation, ingredient_question, order_support, policy_faq, "
            "medical_safety, escalation, general.\n"
            f"Customer profile: {json.dumps(profile)}\n"
            f"Recent conversation:\n{recent}\n"
            f"Latest message: {message}\n"
            "Return only the intent label."
        )
        result = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=message)])
        content = str(getattr(result, "content", "")).strip().lower()
        valid = {
            "product_recommendation",
            "ingredient_question",
            "order_support",
            "policy_faq",
            "medical_safety",
            "escalation",
            "general",
        }
        if content in valid:
            return content  # type: ignore[return-value]
    except Exception:
        return None
    return None


def _classify_intent(
    message: str,
    history: list[dict[str, str]],
    profile: dict[str, Any],
    last_intent: str | None = None,
) -> Intent:
    if _is_affirmative(message) and (
        last_intent == "product_recommendation"
        or _last_assistant_offered_routine(history)
        or _is_ingredient_product_followup(message, history, last_intent)
    ):
        return "product_recommendation"

    llm_intent = _classify_intent_llm(message, history, profile)
    if llm_intent:
        return llm_intent
    return _classify_intent_rules(message)


def _format_products(products: list[Product]) -> str:
    if not products:
        return "No matching products found in the current store catalog."

    lines = []
    for index, product in enumerate(products, start=1):
        lines.append(
            f"{index}. {product.title} ({product.price})\n"
            f"   Description: {product.description}\n"
            f"   Ingredients: {product.ingredients}\n"
            f"   Collections: {', '.join(product.collections or [])}"
        )
    return "\n".join(lines)


def _intent_instructions(intent: str) -> str:
    instructions = {
        "product_recommendation": (
            "Act as a beauty advisor. Use skin-types, skin-concerns, routine-formulas, and active-ingredients knowledge when advising. "
            "Match the customer's current concern or goal first — do not assume oily skin for acne. "
            "For acne or breakout questions, prioritize cleansers, BHA/salicylic treatments, and serums before moisturizers. "
            "For dryness, prioritize rich moisturizers and barrier-repair ingredients. For dark spots, prioritize vitamin C serums and SPF. "
            "If they asked for a product type (e.g. sunscreen), recommend only that type unless they broaden the ask. "
            "Ask one focused follow-up for skin type only when it would materially change the recommendation. "
            "Recommend 1-3 matching products with short reasons. Do not repeat full product descriptions verbatim. "
            "If the customer agreed to a routine, build a concise morning and/or night routine using only products we carry. "
            "Speak as the store's advisor — say 'our store' or 'we carry', never 'your catalog' (the customer does not own inventory)."
        ),
        "ingredient_question": (
            "Answer ingredient compatibility and usage questions directly in plain language. "
            "State clearly whether ingredients can be combined, and if so whether to alternate nights or separate AM/PM. "
            "Do not dump unrelated policy or pregnancy sections unless the customer asked about pregnancy. "
            "Do not invent ingredient interactions that are not supported by the provided context."
        ),
        "order_support": (
            "Use only the order context provided. If order details are missing, ask for order number and checkout email. "
            "Never guess tracking numbers or delivery dates."
        ),
        "policy_faq": (
            "Answer only the specific policy topic asked (shipping, returns, or store FAQ). "
            "Use short bullet points in plain language. Do not mix unrelated policies in one answer. "
            "If the policy context does not contain the answer, say what you do know and offer to escalate."
        ),
        "medical_safety": (
            "Do not diagnose or prescribe. Acknowledge the concern empathetically and clearly recommend seeing a dermatologist. "
            "You may share only high-level, non-medical skincare safety guidance."
        ),
        "escalation": (
            "Acknowledge frustration, explain that a human specialist will take over, and avoid making promises about refunds or outcomes."
        ),
        "general": (
            "Be helpful and guide the customer toward product discovery, ingredient help, order support, or policy questions."
        ),
    }
    return instructions.get(intent, instructions["general"])


def _build_system_prompt(intent: str, context: dict[str, Any]) -> str:
    return (
        "You are an expert skincare advisor and customer support assistant for a Shopify beauty store.\n"
        "Rules:\n"
        "- Use ONLY the store catalog, knowledge context, order context, and customer profile provided below.\n"
        "- Never invent products, prices, order statuses, tracking numbers, or policies.\n"
        "- If required data is missing, ask a short clarifying question.\n"
        "- Never diagnose diseases, prescribe medication, or claim medical cures.\n"
        "- Keep responses conversational, clear, and under 180 words unless building a routine.\n"
        "- Never show raw document filenames, chunk markers, or unedited policy excerpts to the customer.\n"
        "- Summarize policies in plain language with short bullet points when helpful.\n"
        "- Use conversation history for short replies like 'yes' or skin-type-only answers.\n"
        "- Never recommend cleansers or hand creams when the customer asked for sunscreen.\n"
        "- Speak to shoppers as the store's advisor. Say 'our store' or 'we carry' — never 'your catalog' or 'your store catalog'.\n"
        f"Active intent: {intent}\n"
        f"Intent instructions: {_intent_instructions(intent)}\n"
        f"Customer profile: {json.dumps(context.get('profile', {}))}\n"
        f"Store catalog:\n{context.get('products', 'No products available.')}\n"
        f"Knowledge context:\n{context.get('knowledge', 'No knowledge retrieved.')}\n"
        f"Order context:\n{context.get('orders', 'No order data retrieved.')}"
    )


POLICY_TOPIC_ANSWERS: dict[str, dict[str, Any]] = {
    "shipping": {
        "lead": "Yes, we offer international shipping.",
        "bullets": [
            "We ship to most international destinations.",
            "International delivery typically takes 7-14 business days.",
            "Customers are responsible for customs duties, import taxes, and local fees.",
            "Tracking is provided when the carrier supports it in the destination country.",
        ],
    },
    "returns": {
        "lead": "Here is our return and refund policy:",
        "bullets": [
            "Unopened and unused products may be returned within 30 days of delivery.",
            "Opened products may be returned only if defective, damaged on arrival, or the wrong item was shipped.",
            "Refunds are processed within 5-7 business days after we receive and inspect the return.",
            "To start a return, contact support with your order number.",
        ],
    },
    "general": {
        "lead": "Here is what I can share from our store policies:",
        "bullets": [
            "Orders over $50 qualify for free standard shipping in the US.",
            "Unopened products may be returned within 30 days of delivery.",
            "All products are cruelty-free and dermatologist-tested.",
        ],
    },
}


def _is_policy_header(point: str) -> bool:
    lowered = point.lower()
    if "glow beauty" in lowered:
        return True
    if re.search(r"\b(policy|shipping|returns?|refund|tracking|restrictions)\.?$", lowered):
        return True
    if re.search(r"\((united states|us)\)", lowered):
        return True
    return len(point.split()) <= 4


def _extract_knowledge_points(text: str, query_terms: set[str], limit: int = 4) -> list[str]:
    points: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if line.startswith("- "):
            point = line[2:].strip()
        elif line.startswith("• "):
            point = line[2:].strip()
        else:
            continue
        point = point.strip(" .")
        if len(point) < 18 or _is_policy_header(point):
            continue
        points.append(point if point.endswith(".") else f"{point}.")

    if not points:
        cleaned = re.sub(r"\s+", " ", text).strip()
        for part in re.split(r"\s*-\s+", cleaned):
            point = part.strip(" .")
            if len(point) < 18 or _is_policy_header(point):
                continue
            points.append(point if point.endswith(".") else f"{point}.")

    ranked = sorted(
        points,
        key=lambda point: sum(1 for term in query_terms if term in point.lower()),
        reverse=True,
    )
    unique: list[str] = []
    seen: set[str] = set()
    for point in ranked:
        key = point[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
        if len(unique) >= limit:
            break
    return unique


def _policy_fallback_answer(message: str, knowledge_hits: list[dict[str, Any]]) -> str:
    topic = detect_policy_topic(message)
    template = POLICY_TOPIC_ANSWERS.get(topic, POLICY_TOPIC_ANSWERS["general"])
    scoped_hits = filter_policy_hits(knowledge_hits, topic)

    query_terms = set(re.findall(r"[a-z0-9]{3,}", message.lower()))
    points: list[str] = []
    for hit in scoped_hits[:2]:
        points.extend(_extract_knowledge_points(hit.get("text", ""), query_terms, limit=4))

    if len(points) < 2:
        points = list(template["bullets"])

    body = "\n".join(f"- {point}" for point in points[:4])
    return f"{template['lead']}\n{body}\n\nLet me know if you want help with a product or order next."


def _extract_compatibility_lines(text: str, ingredients: list[str]) -> list[str]:
    lines: list[str] = []
    ingredient_terms = _ingredient_terms(ingredients)
    for raw_line in text.split("\n"):
        line = raw_line.strip().lstrip("-•").strip()
        if len(line) < 24:
            continue
        lowered = line.lower()
        if not any(term in lowered for term in ingredient_terms):
            continue
        if (
            "+" in line
            or "together" in lowered
            or "combine" in lowered
            or "alternate" in lowered
            or "same night" in lowered
            or "avoid" in lowered
        ):
            lines.append(line if line.endswith(".") else f"{line}.")
    return lines


def _ingredient_pair_answer(message: str) -> str | None:
    ingredients = _extract_mentioned_ingredients(message)
    if len(ingredients) < 2:
        return None
    return INGREDIENT_PAIR_ANSWERS.get(frozenset(ingredients[:2]))


def _ingredient_fallback_answer(message: str, knowledge_hits: list[dict[str, Any]]) -> str:
    if not knowledge_hits:
        return (
            "I can help with ingredient questions once the store knowledge base is loaded. "
            "Tell me which ingredients or products you are comparing."
        )

    pair_answer = _ingredient_pair_answer(message)
    if pair_answer:
        return f"{pair_answer}\n\nI can also suggest suitable products from our store if you'd like."

    ingredients = _extract_mentioned_ingredients(message)
    query_terms = set(re.findall(r"[a-z0-9]{3,}", message.lower()))
    points: list[str] = []
    for hit in knowledge_hits[:3]:
        points.extend(_extract_compatibility_lines(hit.get("text", ""), ingredients))
        if len(points) >= 3:
            break
    if not points:
        for hit in knowledge_hits[:2]:
            points.extend(_extract_knowledge_points(hit.get("text", ""), query_terms, limit=3))
            if len(points) >= 3:
                break

    if not points and ingredients:
        names = " and ".join(ingredients)
        return (
            f"I can help with {names} layering. Introduce one active at a time, moisturize after treatments, "
            f"and use SPF daily. Tell me your skin type if you want product picks from our store."
        )

    body = "\n".join(f"- {point}" for point in points[:3])
    return f"Here is guidance based on our ingredient knowledge:\n{body}\n\nI can also suggest suitable products if you'd like."


def _sanitize_product_summary(product: Product) -> str:
    description = re.sub(r"\s+", " ", product.description or "").strip()
    if "Key ingredients:" in description:
        description = description.split("Key ingredients:")[0].strip()
    if len(description) > 140:
        description = description[:140].rsplit(" ", 1)[0] + "..."
    ingredients = (product.ingredients or "").strip()
    if ingredients and ingredients not in description:
        return f"{description} Ingredients: {ingredients}."
    return description or "A matching option we carry."


def _wants_routine_build(message: str, history: list[dict[str, str]], last_intent: str | None) -> bool:
    if _is_affirmative(message):
        return last_intent == "product_recommendation" or _last_assistant_offered_routine(history)
    return any(term in message.lower() for term in ["routine", "morning routine", "night routine", "build a"])


def _pick_routine_products(products: list[Product], profile: dict[str, Any]) -> dict[str, Product | None]:
    slots = {"cleanser": None, "serum": None, "moisturizer": None, "sunscreen": None}
    for product in products:
        haystack = f"{product.title} {product.description or ''} {' '.join(product.collections or [])}".lower()
        if slots["sunscreen"] is None and ("sunscreen" in haystack or "spf" in haystack):
            slots["sunscreen"] = product
        elif slots["cleanser"] is None and ("cleanser" in haystack or "cleansing" in haystack or "wash" in haystack):
            slots["cleanser"] = product
        elif slots["serum"] is None and ("serum" in haystack or "essence" in haystack):
            slots["serum"] = product
        elif slots["moisturizer"] is None and any(term in haystack for term in ["moistur", "cream", "lotion", "gel"]):
            slots["moisturizer"] = product
    return slots


def _routine_fallback_answer(products: list[Product], profile: dict[str, Any]) -> str:
    slots = _pick_routine_products(products, profile)
    skin = profile.get("skin_type", "your skin type")
    lines = [f"Here is a simple routine for {skin} skin using products we carry:"]
    morning = []
    if slots["cleanser"]:
        morning.append(f"1. Cleanser — {slots['cleanser'].title}")
    if slots["serum"]:
        morning.append(f"2. Serum — {slots['serum'].title}")
    if slots["moisturizer"]:
        morning.append(f"3. Moisturizer — {slots['moisturizer'].title}")
    if slots["sunscreen"]:
        morning.append(f"4. Sunscreen — {slots['sunscreen'].title}")
    if morning:
        lines.append("Morning:")
        lines.extend(morning)
    night = []
    if slots["cleanser"]:
        night.append(f"1. Cleanser — {slots['cleanser'].title}")
    if slots["serum"]:
        night.append(f"2. Treatment serum — {slots['serum'].title}")
    if slots["moisturizer"]:
        night.append(f"3. Moisturizer — {slots['moisturizer'].title}")
    if night:
        lines.append("Night:")
        lines.extend(night)
    if len(lines) == 1:
        return "I can build a routine once we have a cleanser, serum, moisturizer, and sunscreen available in our store."
    return "\n".join(lines)


def _concern_product_reason(product: Product, concern: str) -> str:
    haystack = _product_haystack(product)
    config = CONCERN_SIGNALS.get(concern, {})
    ingredient_hits = [term for term in config.get("ingredients", []) if term in haystack]
    if ingredient_hits:
        return f"contains {ingredient_hits[0]}"
    tag_hits = [term for term in config.get("tags", []) if term in haystack]
    if tag_hits:
        return f"good for {tag_hits[0]}"
    return _sanitize_product_summary(product)


def _product_haystack(product: Product) -> str:
    return " ".join(
        filter(
            None,
            [
                product.title,
                product.description or "",
                product.ingredients or "",
                " ".join(product.collections or []),
            ],
        )
    ).lower()


def _ingredient_product_fallback_answer(
    products: list[Product],
    history: list[dict[str, str]],
    context: dict[str, Any],
) -> str:
    prior = context.get("prior_user_message") or _recent_substantive_user_message(history)
    ingredients = context.get("mentioned_ingredients") or _extract_mentioned_ingredients(prior)
    picks = _pick_products_for_ingredients(products, ingredients, limit=3)

    if not picks:
        return (
            "I couldn't find a strong match in our store right now. Tell me your skin type and I can suggest "
            "the closest alternatives."
        )

    if len(ingredients) >= 2:
        label = f"{' and '.join(ingredients[:2]).title()}"
        opener = (
            f"Here are options from our store that support a {label} routine "
            f"(alternate nights when starting — not same night):"
        )
    elif ingredients:
        opener = f"Here are products with {ingredients[0]} that we carry:"
    else:
        opener = "Here are relevant products from our store:"

    lines = [opener]
    for index, product in enumerate(picks, start=1):
        lines.append(f"{index}. {product.title} ({product.price}) — {_sanitize_product_summary(product)}")
    lines.append(
        "Use one active treatment per night when starting, moisturize after, and apply SPF every morning."
    )
    return " ".join(lines)


def _product_fallback_answer(
    state: AgentState,
    products: list[Product],
    profile: dict[str, Any],
    history: list[dict[str, str]],
    last_intent: str | None,
) -> str:
    context = state.get("context", {})
    if context.get("ingredient_followup") or _is_ingredient_product_followup(
        state["user_message"], history, last_intent
    ):
        return _ingredient_product_fallback_answer(products, history, context)

    if _wants_routine_build(state["user_message"], history, last_intent) and products:
        return _routine_fallback_answer(products, profile)

    retrieval_query = build_retrieval_query(state["user_message"], profile=profile, history=history)
    requested_types = detect_requested_product_types(retrieval_query)
    concerns = detect_concerns(retrieval_query, profile)
    scoped = filter_products_for_query(products, retrieval_query)

    if not scoped:
        return (
            "I'd love to help. Tell me your skin type, main concerns, and whether you want a single product or a full routine."
        )

    skin_type = profile.get("skin_type")

    if not skin_type and state["user_message"].lower().strip() in {s.lower() for s in SKIN_TYPES}:
        pass
    elif not skin_type and not concerns and len(state["user_message"].split()) <= 4:
        names = ", ".join(item.title for item in scoped[:3])
        return f"I can help with that. We carry options like: {names}. What is your skin type and main concern?"

    if concerns and not requested_types:
        picks = pick_products_for_concerns(scoped, concerns, limit=3)
        primary = concerns[0]
        label = concern_label(primary)
        lines = [f"For {label}, I'd start with these from our store:"]
        for index, product in enumerate(picks, start=1):
            reason = _concern_product_reason(product, primary)
            lines.append(f"{index}. {product.title} ({product.price}) — {reason}.")
        if not skin_type:
            lines.append(
                "What's your skin type (oily, dry, combination, or sensitive)? "
                "That helps me fine-tune cleanser and moisturizer choices."
            )
        else:
            lines.append("Would you like me to build a morning and night routine from these?")
        return " ".join(lines)

    lead = scoped[0]
    extras = [item for item in scoped[1:3] if item.id != lead.id]
    if skin_type:
        opener = f"For {skin_type} skin, I'd start with {lead.title} ({lead.price})."
    else:
        opener = f"I'd start with {lead.title} ({lead.price})."
    response = f"{opener} {_sanitize_product_summary(lead)}"
    if extras:
        names = ", ".join(item.title for item in extras)
        response += f" Other strong options: {names}."
    if requested_types == {"sunscreen"} or "sunscreen" in retrieval_query.lower():
        response += " Apply sunscreen as the last step every morning."
    else:
        response += " Would you like me to build a morning and night routine from these?"
    return response


def _fallback_response(state: AgentState, history: list[dict[str, str]], last_intent: str | None = None) -> str:
    intent = state["intent"]
    context = state["context"]
    products = context.get("product_objects", [])
    knowledge_hits = context.get("knowledge_hits", [])
    orders = context.get("orders", "")

    if intent == "medical_safety":
        return (
            "Your concern may require professional evaluation. I can share general skincare guidance, "
            "but I cannot diagnose conditions or prescribe treatment. Please consult a dermatologist "
            "for personalized medical advice."
        )

    if intent == "escalation":
        return (
            "I understand this needs extra attention. I'm flagging this conversation for a human specialist "
            "who can review your case and follow up shortly."
        )

    if intent == "order_support":
        if orders:
            return (
                f"I found your order details:\n{orders}\n"
                "If this is not the right order, share your order number and the email used at checkout."
            )
        return (
            "I can help check order status. Please share your order number (for example, #3452) "
            "and the email used at checkout."
        )

    if intent == "policy_faq":
        return _policy_fallback_answer(state["user_message"], knowledge_hits)

    if intent == "ingredient_question":
        return _ingredient_fallback_answer(state["user_message"], knowledge_hits)

    if intent == "product_recommendation" and products:
        return _product_fallback_answer(state, products, context.get("profile", {}), history, last_intent)

    if products:
        return _product_fallback_answer(state, products, context.get("profile", {}), history, last_intent)

    return (
        "I'd love to help. Tell me your skin type, main concerns, and whether you want a single product or a full routine."
    )


def _llm_response(
    state: AgentState,
    history: list[dict[str, str]],
    last_intent: str | None = None,
) -> str:
    if not settings.OPENAI_API_KEY:
        return _fallback_response(state, history, last_intent)

    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_CHAT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=INTENT_TEMPERATURES.get(state["intent"], settings.OPENAI_TEMPERATURE),
        )
        history_messages = []
        for item in history[-settings.CHAT_HISTORY_LIMIT :]:
            if item["role"] == "user":
                history_messages.append(HumanMessage(content=item["content"]))
            else:
                history_messages.append(AIMessage(content=item["content"]))

        messages = [
            SystemMessage(content=_build_system_prompt(state["intent"], state["context"])),
            *history_messages,
            HumanMessage(content=state["user_message"]),
        ]
        result = llm.invoke(messages)
        content = getattr(result, "content", "")
        if isinstance(content, str) and content.strip():
            return _polish_customer_reply(content.strip())
    except Exception:
        pass

    return _polish_customer_reply(_fallback_response(state, history, last_intent))


def _extract_profile(message: str, existing: dict[str, Any]) -> dict[str, Any]:
    profile = dict(existing)
    lowered = message.lower()

    if "combination" in lowered and "dry" in lowered:
        profile["skin_type"] = "combination"
    elif "combination" in lowered and "oily" in lowered:
        profile["skin_type"] = "combination"
    else:
        for skin_type in SKIN_TYPES:
            if skin_type in lowered:
                profile["skin_type"] = skin_type

    concerns = list(profile.get("concerns", []))
    if "hydrating" in lowered or "hydration" in lowered or "dehydrated" in lowered:
        if "dehydration" not in concerns:
            concerns.append("dehydration")
    for concern in PROFILE_CONCERNS:
        if concern in lowered and concern not in concerns:
            concerns.append(concern)
    for concern_key, config in CONCERN_SIGNALS.items():
        if any(term in lowered for term in config["match"]):
            mapped = {
                "acne": "acne",
                "aging": "fine lines",
                "dryness": "dehydration",
                "sensitivity": "redness",
                "hyperpigmentation": "hyperpigmentation",
                "redness": "redness",
            }.get(concern_key, concern_key)
            if mapped not in concerns:
                concerns.append(mapped)
    if concerns:
        profile["concerns"] = concerns

    if any(term in lowered for term in ["fragrance-free", "fragrance free", "no fragrance"]):
        profile["preferences"] = "fragrance-free"
    if any(term in lowered for term in ["budget", "affordable", "cheaper", "low cost", "reasonable price", "reasonable"]):
        profile["budget"] = "budget-friendly"
    if any(term in lowered for term in ["premium", "luxury", "high-end"]):
        profile["budget"] = "premium"

    return profile


def _node_classify(
    state: AgentState,
    history: list[dict[str, str]],
    profile: dict[str, Any],
    last_intent: str | None = None,
) -> AgentState:
    state["intent"] = _classify_intent(state["user_message"], history, profile, last_intent=last_intent)
    state["should_escalate"] = state["intent"] == "escalation"
    return state


def _node_gather_context(
    state: AgentState,
    db: Session,
    history: list[dict[str, str]],
    profile: dict[str, Any],
    last_intent: str | None = None,
) -> AgentState:
    ingredient_followup = _is_ingredient_product_followup(state["user_message"], history, last_intent)
    prior_user_message = _recent_substantive_user_message(history) if ingredient_followup else ""
    mentioned_ingredients = _extract_mentioned_ingredients(prior_user_message) if prior_user_message else []

    active_profile = effective_profile_for_retrieval(state["user_message"], profile)
    if ingredient_followup:
        active_profile = {
            key: value
            for key, value in active_profile.items()
            if key not in {"concerns", "skin_type"}
        }

    retrieval_query = build_retrieval_query(state["user_message"], profile=active_profile, history=history)
    if ingredient_followup and prior_user_message:
        ingredient_query = " ".join(_ingredient_terms(mentioned_ingredients))
        retrieval_query = f"{prior_user_message}. {ingredient_query} serum treatment exfoliant products"

    product_limit = settings.PRODUCT_TOP_K
    if _wants_routine_build(state["user_message"], history, last_intent):
        retrieval_query = f"{retrieval_query}. morning night routine cleanser serum moisturizer sunscreen"
        product_limit = max(settings.PRODUCT_TOP_K, 15)
    elif state["intent"] == "product_recommendation":
        product_limit = max(settings.PRODUCT_TOP_K, 8)

    building_routine = _wants_routine_build(state["user_message"], history, last_intent)
    products = search_products(
        db,
        retrieval_query,
        state["store_id"],
        profile=active_profile,
        limit=product_limit,
        enforce_product_type=not building_routine,
    )
    policy_topic = detect_policy_topic(state["user_message"]) if state["intent"] == "policy_faq" else None
    knowledge_hits = search_knowledge(
        db,
        retrieval_query,
        state["store_id"],
        intent=state["intent"],
        policy_topic=policy_topic,
    )
    document_hits = [hit for hit in knowledge_hits if hit.get("type") != "product"]
    if policy_topic:
        document_hits = filter_policy_hits(document_hits, policy_topic)
    elif state["intent"] == "ingredient_question":
        document_hits = filter_ingredient_hits(document_hits, retrieval_query)
    knowledge_text = format_knowledge_context(document_hits)

    orders_text = ""
    order_match = re.search(r"#?(\d{3,6})", state["user_message"])
    if order_match:
        order_number = f"#{order_match.group(1)}"
        order = (
            db.query(Order)
            .filter(Order.store_id == state["store_id"], Order.shopify_order_id == order_number)
            .first()
        )
        if order:
            orders_text = (
                f"Order {order.shopify_order_id} status: {order.status}. "
                f"Tracking number: {order.tracking_number or 'not available yet'}."
            )
        else:
            orders_text = f"No order found for {order_number}. Ask the customer to verify the order number and checkout email."
    elif state["intent"] == "order_support":
        orders_text = "No order number provided yet. Ask for order number and checkout email before stating any order status."

    state["context"] = {
        "products": _format_products(products),
        "product_objects": products,
        "knowledge": knowledge_text,
        "knowledge_hits": document_hits,
        "policy_topic": policy_topic,
        "orders": orders_text,
        "profile": active_profile,
        "ingredient_followup": ingredient_followup,
        "mentioned_ingredients": mentioned_ingredients,
        "prior_user_message": prior_user_message,
    }
    state["sources"] = [hit["source"] for hit in knowledge_hits]
    return state


def _node_respond(
    state: AgentState,
    db: Session,
    history: list[dict[str, str]],
    last_intent: str | None = None,
) -> AgentState:
    state["response"] = _polish_customer_reply(_llm_response(state, history, last_intent=last_intent))

    conversation = db.query(Conversation).filter(Conversation.id == state["conversation_id"]).first()
    if conversation:
        profile = _extract_profile(state["user_message"], (conversation.meta or {}).get("profile", {}))
        conversation.meta = {**(conversation.meta or {}), "profile": profile, "last_intent": state["intent"]}
        if state["should_escalate"]:
            conversation.is_escalated = True
            conversation.status = "escalated"
        db.add(conversation)

    return state


def build_agent_graph(
    db: Session,
    history: list[dict[str, str]],
    profile: dict[str, Any],
    last_intent: str | None = None,
):
    graph = StateGraph(AgentState)
    graph.add_node("classify", lambda state: _node_classify(state, history, profile, last_intent))
    graph.add_node("gather_context", lambda state: _node_gather_context(state, db, history, profile, last_intent))
    graph.add_node("respond", lambda state: _node_respond(state, db, history, last_intent))
    graph.set_entry_point("classify")
    graph.add_edge("classify", "gather_context")
    graph.add_edge("gather_context", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def generate_agent_reply(
    db: Session,
    *,
    store_id: int,
    conversation_id: int,
    user_message: str,
) -> dict[str, Any]:
    history = [
        {"role": message.role, "content": message.content}
        for message in (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
    ]

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    profile = (conversation.meta or {}).get("profile", {}) if conversation else {}
    profile = _extract_profile(user_message, profile)
    last_intent = (conversation.meta or {}).get("last_intent") if conversation else None

    initial_state: AgentState = {
        "store_id": store_id,
        "conversation_id": conversation_id,
        "user_message": user_message,
        "intent": "general",
        "context": {},
        "response": "",
        "should_escalate": False,
        "sources": [],
    }

    graph = build_agent_graph(db, history, profile, last_intent=last_intent)
    result = graph.invoke(initial_state)
    return {
        "content": result["response"],
        "intent": result["intent"],
        "should_escalate": result["should_escalate"],
        "sources": result.get("sources", []),
    }
