from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Message, Order, Product, Store
from app.services.product_links import build_product_url, format_product_markdown_link
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
    is_skin_type_only_message,
    pick_products_for_concerns,
    resolve_recommendation_concerns,
    search_knowledge,
    search_products,
    _concern_score,
    _contains_phrase,
    _product_matches_type,
    _skin_type_score,
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

HAIR_CONCERN_KEYS = frozenset({"hair_fall", "dandruff", "frizz", "dry_hair", "curly_hair"})

HAIR_TOPIC_TERMS = (
    "hair fall",
    "hair loss",
    "shampoo",
    "conditioner",
    "scalp",
    "dandruff",
    "frizz",
    "frizzy",
    "curly hair",
    "wavy hair",
    "dry hair",
    "damaged hair",
    "hair oil",
    "hair mask",
    "hair serum",
    "hair care routine",
    "haircare routine",
    "thinning hair",
    "hijab-friendly",
)

EXPLICIT_HAIR_SIGNALS = HAIR_TOPIC_TERMS + ("haircare",)

SKINCARE_SIGNAL_TERMS = (
    "skincare",
    "moisturizer",
    "cleanser",
    "sunscreen",
    "spf",
    "serum",
    "toner",
    "exfoliant",
    "face wash",
    "facial",
    "complexion",
    "dark spot",
    "wrinkle",
    "pimple",
    "breakout",
)

SKIN_ROUTINE_PHRASES = (
    "morning routine",
    "night routine",
    "skincare routine",
    "am routine",
    "pm routine",
    "evening routine",
)

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
    "shampoo",
    "conditioner",
    "hair oil",
    "hair serum",
    "hair mask",
    "hair fall",
    "dandruff",
    "frizz",
    "curly hair",
    "scalp",
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
            return (
                "routine" in lowered
                or "morning" in lowered
                or "night" in lowered
                or "hair care routine" in lowered
            )
    return False


def _topic_context_from_user_turn(
    message: str,
    history: list[dict[str, str]],
    profile: dict[str, Any],
) -> str:
    """User-only context for skincare vs hair routing (ignore generic assistant greetings)."""
    parts: list[str] = []
    if _is_affirmative(message):
        prior = _recent_substantive_user_message(history)
        if prior:
            parts.append(prior)
    if message.strip():
        parts.append(message)
    if profile.get("skin_type"):
        parts.append(str(profile["skin_type"]))
    if profile.get("concerns"):
        parts.append(" ".join(str(concern) for concern in profile["concerns"]))
    return " ".join(parts).lower()


def _explicit_hair_signals(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in EXPLICIT_HAIR_SIGNALS)


def _skin_signals(text: str) -> bool:
    lowered = text.lower()
    if any(_contains_phrase(lowered, skin_type) for skin_type in SKIN_TYPES):
        return True
    if any(term in lowered for term in SKINCARE_SIGNAL_TERMS):
        return True
    if any(phrase in lowered for phrase in SKIN_ROUTINE_PHRASES):
        return True
    if "skin" in lowered and not _explicit_hair_signals(lowered):
        return True
    return False


def _last_substantive_assistant_message(history: list[dict[str, str]]) -> str:
    for item in reversed(history):
        if item["role"] != "assistant":
            continue
        content = item["content"].strip()
        if len(content) < 40:
            continue
        if content.lower().startswith("hi!") or "what would you like help with" in content.lower():
            continue
        return content
    return ""


def _assistant_message_is_hair_focused(text: str) -> bool:
    lowered = text.lower()
    return _explicit_hair_signals(lowered) or any(
        phrase in lowered for phrase in ("hair care routine", "shampoo", "conditioner", "scalp treatment")
    )


def _combined_conversation_context(
    message: str,
    history: list[dict[str, str]],
    profile: dict[str, Any],
    *,
    include_last_assistant: bool = True,
) -> str:
    parts: list[str] = []
    if _is_affirmative(message):
        prior = _recent_substantive_user_message(history)
        if prior:
            parts.append(prior)
    if message.strip():
        parts.append(message)
    if include_last_assistant:
        for item in reversed(history):
            if item["role"] == "assistant":
                parts.append(item["content"])
                break
    if profile.get("concerns"):
        parts.append(" ".join(str(concern) for concern in profile["concerns"]))
    return " ".join(parts).lower()


def _is_hair_topic(message: str, history: list[dict[str, str]], profile: dict[str, Any]) -> bool:
    user_context = _topic_context_from_user_turn(message, history, profile)

    if _skin_signals(user_context) and not _explicit_hair_signals(user_context):
        return False

    if any(concern in HAIR_CONCERN_KEYS for concern in detect_concerns(user_context, profile)):
        return True

    if _explicit_hair_signals(user_context):
        return True

    if _is_affirmative(message):
        assistant = _last_substantive_assistant_message(history)
        if assistant:
            if _assistant_message_is_hair_focused(assistant):
                return True
            if _skin_signals(assistant) and not _explicit_hair_signals(assistant):
                return False

    return False


def _is_hair_product(product: Product) -> bool:
    haystack = _product_haystack(product)
    hair_markers = (
        "shampoo",
        "conditioner",
        "hair oil",
        "hair mask",
        "hair serum",
        "scalp treatment",
        "scalp tonic",
        "scalp scrub",
        "leave-in",
        "leave in",
        "hair-care",
        "hair care",
        "hairspray",
        "dry shampoo",
        "edge control",
        "hair set",
    )
    return any(marker in haystack for marker in hair_markers)


def _is_skincare_bundle(product: Product) -> bool:
    title = product.title.lower()
    haystack = _product_haystack(product)
    if any(
        term in haystack
        for term in ("routine set", "skincare set", "starter kit", "starter set", " gift set", "value set")
    ):
        return True
    return bool(re.search(r"\b(set|kit|bundle|duo|trio)\b", title))


NON_FACE_SKINCARE_MARKERS = (
    "hand cream",
    "hand repair",
    "hand lotion",
    "hand balm",
    "for hands",
    "cracked hands",
    "foot cream",
    " heel ",
    "heel cream",
    "for feet",
    "body lotion",
    "body cream",
    "body butter",
    "body moistur",
    "body wash",
    " lip balm",
    " lip mask",
    "lip care",
    "lip treatment",
)

NON_FACE_COLLECTION_MARKERS = (
    "body care",
    "body moistur",
    "hand care",
    "foot care",
    "lip care",
    "body wash",
)

FACE_MOISTURIZER_MARKERS = (
    "moisturizer",
    "moistur",
    "face cream",
    "facial",
    "barrier repair cream",
    "barrier cream",
    "night cream",
    "day cream",
    "gel moisturizer",
    "hydrating gel",
    "sleeping mask",
)

NIGHT_TREATMENT_SERUM_MARKERS = (
    "retinol",
    "retinal",
    "retinoid",
    "glycolic",
    "lactic acid",
    " salicylic",
    " bha",
    " aha",
    "exfoliant",
    "night renewal",
    "night serum",
    "peel",
)

MORNING_SERUM_BOOST_MARKERS = (
    "vitamin c",
    "ascorbic",
    "niacinamide",
    "antioxidant",
    "brightening",
)


def _is_non_face_skincare_product(product: Product) -> bool:
    haystack = _product_haystack(product)
    title = product.title.lower()
    if any(marker in haystack for marker in NON_FACE_SKINCARE_MARKERS):
        return True
    if re.search(r"\bhand\b", title):
        return True
    if re.search(r"\bfoot\b", title):
        return True
    for collection in product.collections or []:
        coll = str(collection).lower()
        if any(marker in coll for marker in NON_FACE_COLLECTION_MARKERS):
            return True
    return False


def _is_face_moisturizer(product: Product) -> bool:
    if _is_non_face_skincare_product(product) or _is_hair_product(product):
        return False
    if _product_matches_type(product, "eye care"):
        return False
    haystack = _product_haystack(product)
    if any(marker in haystack for marker in FACE_MOISTURIZER_MARKERS):
        return True
    for collection in product.collections or []:
        coll = str(collection).lower()
        if "moistur" in coll and "body" not in coll:
            return True
    if "cream" in haystack and any(
        term in haystack for term in ("face", "facial", "skin", "ceramide", "barrier", "hydrat")
    ):
        return True
    return False


def _is_night_treatment_serum(product: Product) -> bool:
    haystack = _product_haystack(product)
    return any(marker in haystack for marker in NIGHT_TREATMENT_SERUM_MARKERS)


def _serum_score_for_routine(product: Product, concerns: list[str], *, morning: bool) -> float:
    score = _concern_score(product, concerns)
    haystack = _product_haystack(product)
    if _is_non_face_skincare_product(product):
        return score - 100.0
    if morning:
        if _is_night_treatment_serum(product):
            score -= 50.0
        if any(marker in haystack for marker in MORNING_SERUM_BOOST_MARKERS):
            score += 10.0
        if "hyaluronic" in haystack:
            score += 5.0
    else:
        if _is_night_treatment_serum(product):
            score += 15.0
        if any(marker in haystack for marker in ("vitamin c", "ascorbic", "sunscreen", " spf")):
            score -= 20.0
    return score


def _moisturizer_score_for_routine(product: Product, concerns: list[str], *, night: bool) -> float:
    score = _concern_score(product, concerns)
    if not _is_face_moisturizer(product):
        return score - 100.0
    haystack = _product_haystack(product)
    if night and any(term in haystack for term in ("night", "retinol", "renewal", "repair cream", "rich")):
        score += 8.0
    elif not night and any(term in haystack for term in ("gel", "lightweight", "oil-free")):
        score += 4.0
    return score


def _filter_face_skincare_products(products: list[Product]) -> list[Product]:
    filtered = [
        product
        for product in products
        if not _is_non_face_skincare_product(product) and not _is_hair_product(product)
    ]
    return filtered or products


def _is_skincare_routine_product(product: Product) -> bool:
    if _is_hair_product(product) or _is_skincare_bundle(product):
        return False
    return _classify_skincare_routine_slot(product) is not None


def _classify_skincare_routine_slot(product: Product) -> str | None:
    if _is_non_face_skincare_product(product):
        return None
    title = product.title.lower()
    haystack = _product_haystack(product)
    is_serum_like = _product_matches_type(product, "serum") and not _product_matches_type(product, "eye care")
    if _product_matches_type(product, "sunscreen"):
        if is_serum_like and "sunscreen" not in title and not re.search(r"\bspf\b", title):
            pass
        else:
            return "sunscreen"
    if _product_matches_type(product, "cleanser"):
        return "cleanser"
    if is_serum_like:
        return "serum"
    if _is_face_moisturizer(product):
        return "moisturizer"
    return None


def _format_product_price(product: Product) -> str:
    price = (product.price or "").strip()
    return price if price else "price in store"


def _format_routine_step(step: int, label: str, product: Product, store: Store | None = None) -> str:
    return f"{step}. {label} — {format_product_markdown_link(store, product)}"


def _classify_hair_product(product: Product) -> str | None:
    haystack = _product_haystack(product)
    title = product.title.lower()
    if "routine set" in haystack or "hair set" in haystack:
        return "bundle"
    if "shampoo" in haystack and "conditioner" not in title:
        return "shampoo"
    if "conditioner" in haystack:
        return "conditioner"
    if any(term in haystack for term in ("hair mask", "deep conditioner")):
        return "weekly_mask"
    if any(
        term in haystack
        for term in ("scalp treatment", "scalp tonic", "scalp scrub", "scalp cream")
    ):
        return "treatment"
    if "hair serum" in haystack or ("serum" in haystack and "hair" in haystack):
        return "treatment"
    if "hair oil" in haystack or ("scalp oil" in haystack):
        return "hair_oil"
    if "leave-in" in haystack or "leave in" in haystack:
        return "leave_in"
    return None


def _routine_offer_phrase(message: str, history: list[dict[str, str]], profile: dict[str, Any]) -> str:
    if _is_hair_topic(message, history, profile):
        return "Would you like me to build a simple hair care routine from these?"
    return "Would you like me to build a morning and night routine from these?"


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


def _format_products(products: list[Product], store: Store | None = None) -> str:
    if not products:
        return "No matching products found in the current store catalog."

    lines = []
    for index, product in enumerate(products, start=1):
        url = build_product_url(store, product) if store else None
        link = format_product_markdown_link(store, product)
        block = (
            f"{index}. {link}\n"
            f"   Description: {product.description}\n"
            f"   Ingredients: {product.ingredients}\n"
            f"   Collections: {', '.join(product.collections or [])}"
        )
        if url:
            block += f"\n   Product URL: {url}"
        lines.append(block)
    return "\n".join(lines)


def _intent_instructions(intent: str) -> str:
    instructions = {
        "product_recommendation": (
            "Act as a beauty advisor for skincare and hair care. Use skin-types, skin-concerns, hair-care, routine-formulas, "
            "and active-ingredients knowledge when advising. "
            "Match the customer's current concern or goal first — do not assume oily skin for acne. "
            "For hair questions (shampoo, hair fall, dandruff, frizz, curls), recommend hair products only — never label shampoo "
            "or conditioner as moisturizer or serum. Use hair routine steps: shampoo, conditioner, scalp treatment/serum, "
            "hair oil or leave-in, and optional weekly mask. Do not use skincare morning/night steps for hair. "
            "For acne or breakout questions, prioritize cleansers, BHA/salicylic treatments, and serums before moisturizers. "
            "For dryness, prioritize rich moisturizers and barrier-repair ingredients. For dark spots, prioritize vitamin C serums and SPF. "
            "If they asked for a product type (e.g. sunscreen or shampoo), recommend only that type unless they broaden the ask. "
            "Ask one focused follow-up for skin type only for skincare — not for hair care. "
            "Recommend 1-3 matching products with short reasons. Do not repeat full product descriptions verbatim. "
            "When naming a product, use markdown links from the catalog Product URL: [Title ($price)](url). "
            "If the customer agreed to a routine, build a concise routine using only products we carry and the correct category "
            "(skincare morning/night OR hair wash-day routine). Always include each product's synced store price in parentheses. "
            "Use markdown product links so customers can open the product page in the store. "
            "Use single products only — never place bundles, sets, or kits in individual cleanser/serum/moisturizer steps. "
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
        "You are an expert beauty advisor (skincare and hair care) and customer support assistant for a Shopify beauty store.\n"
        "Rules:\n"
        "- Use ONLY the store catalog, knowledge context, order context, and customer profile provided below.\n"
        "- Never invent products, prices, order statuses, tracking numbers, or policies.\n"
        "- If required data is missing, ask a short clarifying question.\n"
        "- Never diagnose diseases, prescribe medication, or claim medical cures.\n"
        "- Keep responses conversational, clear, and under 180 words unless building a routine.\n"
        "- Never show raw document filenames, chunk markers, or unedited policy excerpts to the customer.\n"
        "- Summarize policies in plain language with short bullet points when helpful.\n"
        "- Use conversation history for short replies like 'yes' or skin-type-only answers.\n"
        "- If the prior topic was hair care, keep hair care context for 'yes' follow-ups — do not switch to skincare.\n"
        f"- Routine domain for this turn: {context.get('routine_domain', 'auto')}.\n"
        "- Never recommend cleansers or hand creams when the customer asked for sunscreen.\n"
        "- Speak to shoppers as the store's advisor. Say 'our store' or 'we carry' — never 'your catalog' or 'your store catalog'.\n"
        "- When recommending products, use markdown links from the catalog Product URL: [Title ($price)](url).\n"
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


def _pick_skincare_routine_products(
    products: list[Product],
    profile: dict[str, Any] | None = None,
    concerns: list[str] | None = None,
) -> dict[str, Product | None]:
    profile = profile or {}
    concerns = concerns or []
    slot_candidates: dict[str, list[Product]] = {
        "cleanser": [],
        "serum": [],
        "moisturizer": [],
        "sunscreen": [],
    }
    for product in products:
        slot = _classify_skincare_routine_slot(product)
        if slot and _is_skincare_routine_product(product):
            slot_candidates[slot].append(product)

    def rank_candidates(
        candidates: list[Product],
        scorer: Any,
    ) -> list[Product]:
        return sorted(candidates, key=scorer, reverse=True)

    cleanser_ranked = rank_candidates(
        slot_candidates["cleanser"],
        lambda product: _concern_score(product, concerns),
    )
    cleanser = cleanser_ranked[0] if cleanser_ranked else None

    face_moisturizers = [product for product in slot_candidates["moisturizer"] if _is_face_moisturizer(product)]
    day_moisturizers = rank_candidates(
        face_moisturizers,
        lambda product: _moisturizer_score_for_routine(product, concerns, night=False),
    )
    night_moisturizers = rank_candidates(
        face_moisturizers,
        lambda product: _moisturizer_score_for_routine(product, concerns, night=True),
    )
    day_moisturizer = day_moisturizers[0] if day_moisturizers else None
    night_moisturizer = None
    for candidate in night_moisturizers:
        if day_moisturizer and candidate.id == day_moisturizer.id:
            continue
        haystack = _product_haystack(candidate)
        if any(term in haystack for term in ("night", "retinol", "renewal", "repair cream", "rich")):
            night_moisturizer = candidate
            break

    serums = slot_candidates["serum"]
    morning_serum_ranked = rank_candidates(
        serums,
        lambda product: _serum_score_for_routine(product, concerns, morning=True),
    )
    night_serum_ranked = rank_candidates(
        serums,
        lambda product: _serum_score_for_routine(product, concerns, morning=False),
    )
    morning_serum = morning_serum_ranked[0] if morning_serum_ranked else None
    night_serum = None
    for candidate in night_serum_ranked:
        if _is_night_treatment_serum(candidate):
            night_serum = candidate
            break
    if not night_serum:
        for candidate in night_serum_ranked:
            if morning_serum and candidate.id == morning_serum.id:
                continue
            night_serum = candidate
            break

    sunscreen_ranked = rank_candidates(
        slot_candidates["sunscreen"],
        lambda product: _concern_score(product, concerns),
    )
    sunscreen = sunscreen_ranked[0] if sunscreen_ranked else None

    return {
        "cleanser": cleanser,
        "moisturizer": day_moisturizer,
        "night_moisturizer": night_moisturizer,
        "morning_serum": morning_serum,
        "night_serum": night_serum,
        "sunscreen": sunscreen,
    }


def _append_routine_steps(
    lines: list[str],
    section_title: str,
    steps: list[tuple[str, Product]],
    store: Store | None,
    *,
    start_step: int = 1,
) -> int:
    if not steps:
        return start_step
    lines.append(section_title)
    step = start_step
    for label, product in steps:
        lines.append(_format_routine_step(step, label, product, store))
        step += 1
    return step


def _pick_hair_routine_products(
    products: list[Product],
    concerns: list[str],
) -> dict[str, Product | None]:
    slots: dict[str, Product | None] = {
        "shampoo": None,
        "conditioner": None,
        "treatment": None,
        "hair_oil": None,
        "weekly_mask": None,
        "leave_in": None,
        "bundle": None,
    }
    ranked = sorted(
        [product for product in products if _is_hair_product(product)],
        key=lambda product: _concern_score(product, concerns),
        reverse=True,
    )
    for product in ranked:
        slot = _classify_hair_product(product)
        if slot and slots.get(slot) is None:
            slots[slot] = product
    return slots


def _skincare_routine_fallback_answer(
    products: list[Product],
    profile: dict[str, Any],
    message: str = "",
    history: list[dict[str, str]] | None = None,
    store: Store | None = None,
) -> str:
    history = history or []
    query = _topic_context_from_user_turn(message, history, profile)
    concerns = detect_concerns(query, profile)
    picks = _pick_skincare_routine_products(products, profile, concerns)
    skin = profile.get("skin_type")
    wants_morning = "morning" in message.lower() or "am routine" in message.lower()
    wants_night = "night" in message.lower() or "evening" in message.lower() or "pm routine" in message.lower()

    if concerns:
        opener = f"Here is a simple skincare routine for {concern_label(concerns[0])} using products we carry:"
    elif skin:
        opener = f"Here is a simple skincare routine for {skin} skin using products we carry:"
    else:
        opener = "Here is a simple skincare routine using products we carry:"

    lines = [opener]

    morning_only_steps: list[tuple[str, Product]] = []
    if picks["morning_serum"]:
        morning_only_steps.append(("Serum", picks["morning_serum"]))
    if picks["sunscreen"]:
        morning_only_steps.append(("Sunscreen", picks["sunscreen"]))

    night_only_steps: list[tuple[str, Product]] = []
    morning_serum = picks["morning_serum"]
    night_serum = picks["night_serum"]
    if night_serum and (not morning_serum or night_serum.id != morning_serum.id):
        night_only_steps.append(("Treatment serum", night_serum))
    day_moisturizer = picks["moisturizer"]
    night_moisturizer = picks["night_moisturizer"]
    if night_moisturizer and day_moisturizer and night_moisturizer.id != day_moisturizer.id:
        night_only_steps.append(("Night moisturizer", night_moisturizer))

    daily_steps: list[tuple[str, Product]] = []
    if picks["cleanser"]:
        daily_steps.append(("Cleanser", picks["cleanser"]))
    if day_moisturizer:
        daily_steps.append(("Moisturizer", day_moisturizer))

    if wants_morning and not wants_night:
        morning_steps: list[tuple[str, Product]] = []
        if picks["cleanser"]:
            morning_steps.append(("Cleanser", picks["cleanser"]))
        if picks["morning_serum"]:
            morning_steps.append(("Serum", picks["morning_serum"]))
        if day_moisturizer:
            morning_steps.append(("Moisturizer", day_moisturizer))
        if picks["sunscreen"]:
            morning_steps.append(("Sunscreen", picks["sunscreen"]))
        _append_routine_steps(lines, "Morning:", morning_steps, store)
    elif wants_night and not wants_morning:
        night_steps: list[tuple[str, Product]] = []
        if picks["cleanser"]:
            night_steps.append(("Cleanser", picks["cleanser"]))
        if night_serum and (not morning_serum or night_serum.id != morning_serum.id):
            night_steps.append(("Treatment serum", night_serum))
        elif night_serum:
            night_steps.append(("Serum", night_serum))
        if night_moisturizer:
            night_steps.append(("Moisturizer", night_moisturizer))
        elif day_moisturizer:
            night_steps.append(("Moisturizer", day_moisturizer))
        _append_routine_steps(lines, "Night:", night_steps, store)
    else:
        _append_routine_steps(lines, "Every day (morning & night):", daily_steps, store)
        _append_routine_steps(lines, "Morning only:", morning_only_steps, store)
        if night_only_steps:
            _append_routine_steps(lines, "Night only:", night_only_steps, store)
        elif daily_steps:
            lines.append("Night: repeat the cleanser and moisturizer above. Skip sunscreen.")

    if len(lines) == 1:
        return (
            "I can build a skincare routine once we have a cleanser, serum, moisturizer, "
            "and sunscreen available in our store."
        )
    return "\n".join(lines)


def _hair_routine_fallback_answer(
    products: list[Product],
    profile: dict[str, Any],
    message: str,
    history: list[dict[str, str]],
    store: Store | None = None,
) -> str:
    combined = _topic_context_from_user_turn(message, history, profile)
    concerns = [concern for concern in detect_concerns(combined, profile) if concern in HAIR_CONCERN_KEYS]
    if not concerns:
        concerns = ["hair_fall"]
    slots = _pick_hair_routine_products(products, concerns)
    label = concern_label(concerns[0])
    lines = [f"Here is a simple hair care routine for {label} using products we carry:"]

    wash_day: list[str] = []
    step = 1
    if slots["shampoo"]:
        wash_day.append(_format_routine_step(step, "Shampoo", slots["shampoo"], store))
        step += 1
    if slots["conditioner"]:
        wash_day.append(
            f"{_format_routine_step(step, 'Conditioner', slots['conditioner'], store)} (mid-lengths to ends)"
        )
        step += 1
    if wash_day:
        lines.append("Wash day (2-3x per week):")
        lines.extend(wash_day)

    after_wash: list[str] = []
    if slots["treatment"]:
        after_wash.append(_format_routine_step(1, "Scalp treatment / serum", slots["treatment"], store))
    if slots["leave_in"]:
        after_wash.append(
            _format_routine_step(2 if slots["treatment"] else 1, "Leave-in", slots["leave_in"], store)
        )
    elif slots["hair_oil"]:
        after_wash.append(
            f"{_format_routine_step(2 if slots['treatment'] else 1, 'Hair oil', slots['hair_oil'], store)} (ends only)"
        )
    if after_wash:
        lines.append("After wash:")
        lines.extend(after_wash)

    if slots["weekly_mask"]:
        lines.append(f"Weekly: Hair mask — {format_product_markdown_link(store, slots['weekly_mask'])}")

    if slots["bundle"] and len(lines) == 1:
        lines.append(f"Bundle option: {format_product_markdown_link(store, slots['bundle'])}")

    if len(lines) == 1:
        return (
            "I can build a hair care routine once we have shampoo, conditioner, and a scalp or "
            "hair treatment available in our store."
        )

    lines.append(
        "Tips: massage the scalp gently, rinse well, avoid heavy oil on the roots if your scalp is oily, "
        "and reduce heat styling while hair is fragile."
    )
    return "\n".join(lines)


def _routine_fallback_answer(
    products: list[Product],
    profile: dict[str, Any],
    message: str,
    history: list[dict[str, str]],
    store: Store | None = None,
) -> str:
    if _is_hair_topic(message, history, profile):
        return _hair_routine_fallback_answer(products, profile, message, history, store)
    return _skincare_routine_fallback_answer(products, profile, message, history, store)


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
    store: Store | None = None,
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
        link = format_product_markdown_link(store, product)
        lines.append(f"{index}. {link} — {_sanitize_product_summary(product)}")
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
    store = context.get("store")
    if context.get("ingredient_followup") or _is_ingredient_product_followup(
        state["user_message"], history, last_intent
    ):
        return _ingredient_product_fallback_answer(products, history, context, store)

    if _wants_routine_build(state["user_message"], history, last_intent) and products:
        return _routine_fallback_answer(products, profile, state["user_message"], history, store)

    retrieval_query = build_retrieval_query(state["user_message"], profile=profile, history=history)
    requested_types = detect_requested_product_types(retrieval_query)
    concerns = resolve_recommendation_concerns(state["user_message"], profile, history)
    scoped = filter_products_for_query(products, retrieval_query)
    hair_topic = _is_hair_topic(state["user_message"], history, profile)
    if not hair_topic:
        scoped = _filter_face_skincare_products(scoped)

    if not scoped:
        if hair_topic:
            return (
                "I'd love to help with hair care. Tell me your main concern (hair fall, dandruff, "
                "frizz, dryness, or curls) and whether you want a single product or a full routine."
            )
        return (
            "I'd love to help. Tell me your skin type, main concerns, and whether you want a single product or a full routine."
        )

    skin_type = profile.get("skin_type")
    offer = _routine_offer_phrase(state["user_message"], history, profile)

    if not skin_type and state["user_message"].lower().strip() in {s.lower() for s in SKIN_TYPES}:
        pass
    elif not skin_type and not concerns and len(state["user_message"].split()) <= 4:
        names = ", ".join(format_product_markdown_link(store, item, with_price=False) for item in scoped[:3])
        if hair_topic:
            return (
                f"I can help with that. We carry options like: {names}. "
                "What is your main hair concern (hair fall, dandruff, frizz, dryness, or curls)?"
            )
        return f"I can help with that. We carry options like: {names}. What is your skin type and main concern?"

    if concerns and not requested_types:
        ranked_scoped = sorted(
            scoped,
            key=lambda product: _concern_score(product, concerns)
            + (_skin_type_score(product, skin_type) if skin_type else 0.0),
            reverse=True,
        )
        picks = pick_products_for_concerns(ranked_scoped, concerns, limit=3, profile=profile)
        primary = concerns[0]
        label = concern_label(primary)
        if primary in HAIR_CONCERN_KEYS:
            lines = [f"For {label}, I'd start with these from our store:"]
            for index, product in enumerate(picks, start=1):
                reason = _concern_product_reason(product, primary)
                link = format_product_markdown_link(store, product)
                lines.append(f"{index}. {link} — {reason}.")
            lines.append(offer)
            return " ".join(lines)

        if skin_type and is_skin_type_only_message(state["user_message"]):
            opener = f"For {label} on {skin_type} skin, I'd start with these from our store:"
        else:
            opener = f"For {label}, I'd start with these from our store:"
        lines = [opener]
        for index, product in enumerate(picks, start=1):
            reason = _concern_product_reason(product, primary)
            link = format_product_markdown_link(store, product)
            lines.append(f"{index}. {link} — {reason}.")
        if not skin_type:
            lines.append(
                "What's your skin type (oily, dry, combination, or sensitive)? "
                "That helps me fine-tune cleanser and moisturizer choices."
            )
        else:
            lines.append(offer)
        return " ".join(lines)

    lead = scoped[0]
    extras = [item for item in scoped[1:3] if item.id != lead.id]
    lead_link = format_product_markdown_link(store, lead)
    if hair_topic:
        if concerns:
            opener = f"For {concern_label(concerns[0])}, I'd start with {lead_link}."
        else:
            opener = f"For your hair concern, I'd start with {lead_link}."
    elif skin_type:
        opener = f"For {skin_type} skin, I'd start with {lead_link}."
    else:
        opener = f"I'd start with {lead_link}."
    response = f"{opener} {_sanitize_product_summary(lead)}"
    if extras:
        names = ", ".join(format_product_markdown_link(store, item, with_price=False) for item in extras)
        response += f" Other strong options: {names}."
    if requested_types == {"sunscreen"} or "sunscreen" in retrieval_query.lower():
        response += " Apply sunscreen as the last step every morning."
    elif hair_topic:
        response += f" {offer}"
    else:
        response += f" {offer}"
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
    context = state.get("context", {})
    products = context.get("product_objects", [])
    if (
        state["intent"] == "product_recommendation"
        and products
        and _wants_routine_build(state["user_message"], history, last_intent)
    ):
        return _polish_customer_reply(
            _routine_fallback_answer(
                products,
                context.get("profile", {}),
                state["user_message"],
                history,
                context.get("store"),
            )
        )

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
                "hair_fall": "hair fall",
                "dandruff": "dandruff",
                "frizz": "frizz",
                "dry_hair": "dry hair",
                "curly_hair": "curly hair",
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
    if is_skin_type_only_message(state["user_message"]):
        follow_up_concerns = resolve_recommendation_concerns(
            state["user_message"], active_profile, history
        )
        if follow_up_concerns:
            concern_phrase = ", ".join(concern_label(concern) for concern in follow_up_concerns[:2])
            retrieval_query = f"{retrieval_query}. {concern_phrase} serum sunscreen moisturizer"
    if ingredient_followup and prior_user_message:
        ingredient_query = " ".join(_ingredient_terms(mentioned_ingredients))
        retrieval_query = f"{prior_user_message}. {ingredient_query} serum treatment exfoliant products"

    building_routine = _wants_routine_build(state["user_message"], history, last_intent)
    routine_domain = (
        "hair"
        if building_routine and _is_hair_topic(state["user_message"], history, active_profile)
        else "skin"
        if building_routine
        else "none"
    )

    product_limit = settings.PRODUCT_TOP_K
    if building_routine:
        if routine_domain == "hair":
            prior = (
                _recent_substantive_user_message(history)
                if _is_affirmative(state["user_message"])
                else state["user_message"]
            )
            retrieval_query = (
                f"{prior}. hair care routine shampoo conditioner scalp serum treatment hair oil mask"
            )
        else:
            retrieval_query = f"{retrieval_query}. morning night routine cleanser serum moisturizer sunscreen"
        product_limit = max(settings.PRODUCT_TOP_K, 15)
    elif state["intent"] == "product_recommendation":
        product_limit = max(settings.PRODUCT_TOP_K, settings.PRODUCT_SEARCH_LIMIT)
    products = search_products(
        db,
        retrieval_query,
        state["store_id"],
        profile=active_profile,
        limit=product_limit,
        enforce_product_type=not building_routine,
    )
    skincare_context = routine_domain == "skin" or (
        state["intent"] == "product_recommendation"
        and not _is_hair_topic(state["user_message"], history, active_profile)
    )
    if skincare_context:
        products = _filter_face_skincare_products(products)
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

    store = db.query(Store).filter(Store.id == state["store_id"]).first()

    state["context"] = {
        "products": _format_products(products, store),
        "product_objects": products,
        "store": store,
        "knowledge": knowledge_text,
        "knowledge_hits": document_hits,
        "policy_topic": policy_topic,
        "orders": orders_text,
        "profile": active_profile,
        "ingredient_followup": ingredient_followup,
        "mentioned_ingredients": mentioned_ingredients,
        "prior_user_message": prior_user_message,
        "routine_domain": routine_domain,
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
