import math
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EmbeddingRecord, Product


def _split_long_block(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(sentence) <= chunk_size:
            current = sentence
            continue
        start = 0
        while start < len(sentence):
            end = min(start + chunk_size, len(sentence))
            chunks.append(sentence[start:end].strip())
            if end == len(sentence):
                break
            start = max(end - overlap, start + 1)
        current = ""
    if current:
        chunks.append(current)
    return chunks


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    blocks = []
    for block in re.split(r"\n\s*\n", normalized):
        lines = [re.sub(r"[ \t]+", " ", line.strip()) for line in block.split("\n")]
        cleaned = "\n".join(line for line in lines if line)
        if cleaned:
            blocks.append(cleaned)
    if not blocks:
        return []

    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(block) <= chunk_size:
            current = block
        else:
            chunks.extend(_split_long_block(block, chunk_size, overlap))
    if current:
        chunks.append(current)
    return chunks


def build_retrieval_query(
    message: str,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> str:
    parts = [message.strip()]
    profile = profile or {}
    history = history or []

    if profile.get("skin_type"):
        parts.append(f"skin type: {profile['skin_type']}")
    if profile.get("concerns"):
        concerns = ", ".join(profile["concerns"])
        parts.append(f"concerns: {concerns}")
    if profile.get("preferences"):
        parts.append(f"preferences: {profile['preferences']}")
    if profile.get("budget"):
        parts.append(f"budget: {profile['budget']}")

    recent_user_messages = [item["content"] for item in history[-6:] if item["role"] == "user"]
    short_reply = len(message.strip().split()) <= 3
    if short_reply and recent_user_messages:
        parts.append("recent context: " + " | ".join(recent_user_messages[-3:]))
    elif len(recent_user_messages) > 1:
        parts.append("recent context: " + " | ".join(recent_user_messages[:-1]))

    return ". ".join(part for part in parts if part)


REQUESTED_PRODUCT_TYPES: dict[str, list[str]] = {
    "sunscreen": ["sunscreen", "spf", "sunblock", "sun protection"],
    "cleanser": ["cleanser", "cleansing", "face wash", "wash", "foam"],
    "serum": ["serum", "essence", "ampoule"],
    "moisturizer": ["moisturizer", "moistur", "cream", "lotion"],
    "toner": ["toner", "toning"],
    "mask": ["mask", "sheet mask"],
    "exfoliant": ["exfoliant", "peel", "bha", "aha"],
    "spot treatment": ["spot treatment", "pimple patch", "acne patch", "hydrocolloid"],
    "eye care": ["eye cream", "eye serum", "eye gel"],
    "lip care": ["lip balm", "lip mask", "lip treatment"],
}

SKIN_TYPES = ["oily", "dry", "combination", "sensitive", "normal"]

CONCERN_SIGNALS: dict[str, dict[str, Any]] = {
    "acne": {
        "match": [
            "acne",
            "blemish",
            "breakout",
            "pimple",
            "blackhead",
            "whitehead",
            "clogged pore",
            "zit",
            "cystic",
        ],
        "ingredients": [
            "salicylic",
            "bha",
            "niacinamide",
            "tea tree",
            "azelaic",
            "benzoyl",
            "pha",
            "sulfur",
        ],
        "preferred_types": ["cleanser", "serum", "exfoliant", "toner", "spot treatment"],
        "tags": ["acne", "blemish", "bha", "salicylic", "clarif", "non-comedogenic", "spot"],
        "label": "acne prevention",
    },
    "aging": {
        "match": ["fine line", "wrinkle", "anti-aging", "anti aging", "mature skin", "firming"],
        "ingredients": ["retinol", "peptide", "renewal", "collagen", "bakuchiol"],
        "preferred_types": ["serum", "moisturizer", "eye care"],
        "tags": ["anti-aging", "retinol", "peptide", "line", "renewal"],
        "label": "anti-aging",
    },
    "dryness": {
        "match": ["dry skin", "dryness", "dehydrat", "flaky", "tight skin", "barrier repair"],
        "ingredients": ["ceramide", "hyaluronic", "squalane", "shea", "glycerin", "barrier"],
        "preferred_types": ["moisturizer", "serum", "cleanser"],
        "tags": ["dry", "hydrat", "barrier", "ceramide", "repair"],
        "label": "dry or dehydrated skin",
    },
    "sensitivity": {
        "match": ["sensitive", "irritat", "rosacea", "reactive skin"],
        "ingredients": ["fragrance-free", "centella", "aloe", "ceramide", "oat", "soothing"],
        "preferred_types": ["cleanser", "moisturizer", "sunscreen", "serum"],
        "tags": ["sensitive", "gentle", "soothing", "fragrance-free", "barrier"],
        "label": "sensitive skin",
    },
    "hyperpigmentation": {
        "match": [
            "dark spot",
            "hyperpigmentation",
            "uneven tone",
            "melasma",
            "brighten",
            "discoloration",
        ],
        "ingredients": ["vitamin c", "ascorbic", "niacinamide", "azelaic", "tranexamic", "bright"],
        "preferred_types": ["serum", "moisturizer", "sunscreen"],
        "tags": ["bright", "tone", "dark spot", "vitamin c", "hyperpigmentation"],
        "label": "dark spots and uneven tone",
    },
    "redness": {
        "match": ["redness", "red skin", "inflam"],
        "ingredients": ["niacinamide", "centella", "azelaic", "soothing", "aloe"],
        "preferred_types": ["serum", "moisturizer", "cleanser"],
        "tags": ["redness", "soothing", "calm", "rosacea"],
        "label": "redness and irritation",
    },
}


def _contains_phrase(text: str, phrase: str) -> bool:
    lowered = text.lower()
    if " " in phrase:
        return phrase in lowered
    return bool(re.search(rf"\b{re.escape(phrase)}\b", lowered))


def _message_mentions_skin_type(message: str) -> bool:
    return any(_contains_phrase(message, skin_type) for skin_type in SKIN_TYPES)


PROFILE_CONCERN_MAP: dict[str, str] = {
    "acne": "acne",
    "dehydration": "dryness",
    "fine lines": "aging",
    "wrinkles": "aging",
    "hyperpigmentation": "hyperpigmentation",
    "dark spots": "hyperpigmentation",
    "redness": "redness",
    "uneven skin tone": "hyperpigmentation",
    "enlarged pores": "acne",
}


def detect_concerns(query: str, profile: dict[str, Any] | None = None) -> list[str]:
    profile = profile or {}
    lowered = query.lower()
    found: list[str] = []
    for concern, config in CONCERN_SIGNALS.items():
        if any(term in lowered for term in config["match"]):
            found.append(concern)
    for concern in profile.get("concerns", []):
        mapped = PROFILE_CONCERN_MAP.get(str(concern).lower())
        if mapped and mapped not in found:
            found.append(mapped)
    return found


def effective_profile_for_retrieval(message: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Drop stale skin-type bias when the customer asks about a new concern without restating skin type."""
    profile = dict(profile or {})
    query_concerns = detect_concerns(message, None)
    if query_concerns and not _message_mentions_skin_type(message):
        profile.pop("skin_type", None)
    return profile


def concern_label(concern: str) -> str:
    return CONCERN_SIGNALS.get(concern, {}).get("label", concern.replace("_", " "))


def detect_requested_product_types(query: str) -> set[str]:
    lowered = query.lower()
    found: set[str] = set()
    for product_type, terms in REQUESTED_PRODUCT_TYPES.items():
        if any(term in lowered for term in terms):
            found.add(product_type)
    return found


def _product_matches_type(product: Product, product_type: str) -> bool:
    haystack = _product_haystack(product)
    terms = REQUESTED_PRODUCT_TYPES.get(product_type, [product_type])
    if any(term in haystack for term in terms):
        return True
    for collection in product.collections or []:
        if any(term in str(collection).lower() for term in terms):
            return True
    return False


def filter_products_for_query(products: list[Product], query: str) -> list[Product]:
    requested_types = detect_requested_product_types(query)
    if not requested_types:
        return products
    filtered = [product for product in products if any(_product_matches_type(product, product_type) for product_type in requested_types)]
    return filtered or products


def _parse_price_amount(price: str | None) -> float | None:
    if not price:
        return None
    digits = re.sub(r"[^\d.]", "", str(price))
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def _hash_embedding(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        return vector

    for token in tokens:
        bucket = hash(token) % dimension
        vector[bucket] += 1.0

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude:
        vector = [value / magnitude for value in vector]
    return vector


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    if settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception:
            pass

    return [_hash_embedding(text, settings.PGVECTOR_DIMENSION) for text in texts]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def index_product_embeddings(db: Session, store_id: int) -> None:
    products = db.query(Product).filter(Product.store_id == store_id).all()
    existing_records = db.query(EmbeddingRecord).filter(EmbeddingRecord.store_id == store_id).all()
    indexed_product_ids = {
        (record.meta or {}).get("product_id")
        for record in existing_records
        if (record.meta or {}).get("type") == "product"
    }

    for product in products:
        if product.id in indexed_product_ids:
            continue

        product_text = " ".join(
            filter(
                None,
                [
                    product.title,
                    product.description or "",
                    product.ingredients or "",
                    " ".join(product.collections or []),
                    product.price or "",
                ],
            )
        )
        vector = generate_embeddings([product_text])[0]
        db.add(
            EmbeddingRecord(
                store_id=store_id,
                document_id=None,
                chunk_text=product_text,
                vector=vector,
                meta={
                    "source": "product-catalog",
                    "product_id": product.id,
                    "product_title": product.title,
                    "type": "product",
                },
            )
        )


POLICY_SOURCE_HINTS: dict[str, list[str]] = {
    "ship": ["shipping"],
    "shipping": ["shipping"],
    "international": ["shipping", "international"],
    "delivery": ["shipping", "delivery"],
    "tracking": ["shipping", "tracking"],
    "return": ["return", "refund"],
    "refund": ["return", "refund"],
    "exchange": ["return", "refund"],
    "faq": ["store-faq"],
}

POLICY_TOPIC_SOURCES: dict[str, list[str]] = {
    "shipping": ["shipping"],
    "returns": ["return", "refund"],
    "general": ["store-faq", "faq"],
}

POLICY_TOPIC_TERMS: dict[str, list[str]] = {
    "shipping": ["international", "ship", "shipping", "delivery", "tracking", "domestic", "transit"],
    "returns": ["return", "refund", "exchange", "money back"],
}


def detect_policy_topic(query: str) -> str:
    lowered = query.lower()
    scores = {
        topic: sum(1 for term in terms if term in lowered)
        for topic, terms in POLICY_TOPIC_TERMS.items()
    }
    shipping_score = scores["shipping"]
    return_score = scores["returns"]

    if shipping_score and not return_score:
        return "shipping"
    if return_score and not shipping_score:
        return "returns"
    if shipping_score > return_score:
        return "shipping"
    if return_score > shipping_score:
        return "returns"
    return "general"


INGREDIENT_PREFERRED_SOURCES = [
    "ingredient-compatibility",
    "active-ingredients",
    "ingredient-faq",
    "ingredient",
    "product-usage",
]


def filter_ingredient_hits(hits: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    preferred = [
        hit
        for hit in hits
        if any(token in str(hit.get("source", "")).lower() for token in INGREDIENT_PREFERRED_SOURCES)
    ]
    if not preferred:
        return hits

    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    ranked = sorted(
        preferred,
        key=lambda hit: sum(1 for term in query_terms if term in str(hit.get("text", "")).lower()),
        reverse=True,
    )
    return ranked + [hit for hit in hits if hit not in preferred]


def filter_policy_hits(hits: list[dict[str, Any]], topic: str) -> list[dict[str, Any]]:
    preferred = POLICY_TOPIC_SOURCES.get(topic, [])
    if not preferred:
        return hits

    filtered = [
        hit
        for hit in hits
        if any(token in str(hit.get("source", "")).lower() for token in preferred)
    ]
    return filtered or hits

INGREDIENT_SOURCE_HINTS: dict[str, list[str]] = {
    "niacinamide": ["ingredient", "active-ingredients", "compatibility"],
    "vitamin c": ["ingredient", "active-ingredients", "compatibility"],
    "retinol": ["ingredient", "active-ingredients", "compatibility"],
    "salicylic": ["ingredient", "active-ingredients", "skin-concerns"],
    "hyaluronic": ["ingredient", "active-ingredients", "skin-types"],
    "ceramide": ["ingredient", "active-ingredients", "skin-types"],
    "azelaic": ["active-ingredients", "skin-concerns"],
    "benzoyl": ["active-ingredients", "skin-concerns"],
    "glycolic": ["active-ingredients"],
    "lactic": ["active-ingredients"],
    "peptide": ["active-ingredients", "skin-concerns"],
    "ingredient": ["ingredient", "active-ingredients", "compatibility"],
    "layer": ["ingredient", "product-usage", "compatibility"],
    "routine": ["product-usage", "skin-consultation", "routine-formulas"],
    "compatible": ["compatibility", "ingredient"],
    "combine": ["compatibility", "ingredient"],
    "mix": ["compatibility", "ingredient"],
}

SKIN_ADVISORY_SOURCE_HINTS: dict[str, list[str]] = {
    "oily": ["skin-types", "routine-formulas"],
    "dry": ["skin-types", "routine-formulas"],
    "combination": ["skin-types", "routine-formulas"],
    "sensitive": ["skin-types", "skin-concerns", "routine-formulas"],
    "normal": ["skin-types", "routine-formulas"],
    "acne": ["skin-concerns", "active-ingredients", "routine-formulas"],
    "blemish": ["skin-concerns", "active-ingredients"],
    "breakout": ["skin-concerns", "active-ingredients", "routine-formulas"],
    "pimple": ["skin-concerns", "active-ingredients"],
    "wrinkle": ["skin-concerns", "active-ingredients", "routine-formulas"],
    "fine line": ["skin-concerns", "active-ingredients"],
    "aging": ["skin-concerns", "active-ingredients", "routine-formulas"],
    "dark spot": ["skin-concerns", "active-ingredients"],
    "hyperpigmentation": ["skin-concerns", "active-ingredients"],
    "melasma": ["skin-concerns", "active-ingredients"],
    "redness": ["skin-concerns", "skin-types"],
    "rosacea": ["skin-concerns", "skin-types"],
    "dehydrat": ["skin-concerns", "skin-types"],
    "flaky": ["skin-types", "skin-concerns"],
    "pore": ["skin-concerns", "skin-types", "active-ingredients"],
    "dull": ["skin-concerns", "routine-formulas"],
    "texture": ["skin-concerns", "active-ingredients"],
    "recommend": ["skin-concerns", "routine-formulas", "skin-types"],
    "suggest": ["skin-concerns", "routine-formulas", "skin-types"],
    "prevent": ["skin-concerns", "active-ingredients", "routine-formulas"],
    "treatment": ["skin-concerns", "active-ingredients"],
}


def _source_boost(
    query: str,
    source: str,
    intent: str | None = None,
    policy_topic: str | None = None,
) -> float:
    lowered_query = query.lower()
    lowered_source = source.lower()
    boost = 0.0
    if intent == "policy_faq":
        hint_map = POLICY_SOURCE_HINTS
    elif intent == "ingredient_question":
        hint_map = INGREDIENT_SOURCE_HINTS
    elif intent in {"product_recommendation", "general"}:
        hint_map = {**INGREDIENT_SOURCE_HINTS, **SKIN_ADVISORY_SOURCE_HINTS}
    else:
        hint_map = {}

    if intent == "policy_faq" and policy_topic:
        preferred = POLICY_TOPIC_SOURCES.get(policy_topic, [])
        if any(token in lowered_source for token in preferred):
            boost += 0.55
        mismatched_topics = [
            topic
            for topic, tokens in POLICY_TOPIC_SOURCES.items()
            if topic != policy_topic and topic != "general"
            and any(token in lowered_source for token in tokens)
        ]
        if mismatched_topics:
            boost -= 0.45

    for term, preferred_sources in hint_map.items():
        if term not in lowered_query:
            continue
        if any(preferred in lowered_source for preferred in preferred_sources):
            boost += 0.35
        elif intent == "policy_faq" and any(
            blocked in lowered_source for blocked in ("product-usage", "skin-consultation", "ingredient")
        ):
            boost -= 0.3

    query_terms = set(re.findall(r"[a-z0-9]+", lowered_query))
    source_terms = set(re.findall(r"[a-z0-9]+", lowered_source))
    boost += min(len(query_terms & source_terms) * 0.08, 0.24)
    return boost


def _keyword_overlap_boost(query: str, text: str) -> float:
    query_terms = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
    text_terms = set(re.findall(r"[a-z0-9]{3,}", text.lower()))
    if not query_terms:
        return 0.0
    overlap = len(query_terms & text_terms)
    return min(overlap * 0.05, 0.25)


def format_knowledge_context(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "No knowledge retrieved."

    sections: list[str] = []
    seen_text: set[str] = set()
    for hit in hits:
        text = re.sub(r"\s+", " ", hit.get("text", "")).strip()
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        label = re.sub(r"\.(txt|md|pdf)$", "", hit.get("source", "knowledge"), flags=re.IGNORECASE)
        label = label.replace("-", " ").replace("_", " ").strip().title()
        sections.append(f"{label}:\n{text}")
    return "\n\n".join(sections) if sections else "No knowledge retrieved."


def search_knowledge(
    db: Session,
    query: str,
    store_id: int,
    limit: int | None = None,
    include_products: bool = False,
    intent: str | None = None,
    policy_topic: str | None = None,
) -> list[dict[str, Any]]:
    limit = limit or settings.RAG_TOP_K
    records = db.query(EmbeddingRecord).filter(EmbeddingRecord.store_id == store_id).all()
    if not records:
        return []

    if not include_products:
        records = [record for record in records if (record.meta or {}).get("type") != "product"]

    query_vector = generate_embeddings([query])[0]
    scored = [
        {
            "text": record.chunk_text,
            "source": (record.meta or {}).get("source", "knowledge-base"),
            "product_id": (record.meta or {}).get("product_id"),
            "product_title": (record.meta or {}).get("product_title"),
            "type": (record.meta or {}).get("type", "document"),
            "score": _cosine_similarity(query_vector, record.vector)
            + _source_boost(
                query,
                (record.meta or {}).get("source", ""),
                intent=intent,
                policy_topic=policy_topic,
            )
            + _keyword_overlap_boost(query, record.chunk_text)
            + (0.18 if (record.meta or {}).get("type") == "chat-learned" else 0.0),
        }
        for record in records
    ]
    scored = [item for item in scored if item["score"] >= settings.RAG_MIN_SCORE]
    scored.sort(key=lambda item: item["score"], reverse=True)
    if intent == "policy_faq" and policy_topic:
        scored = filter_policy_hits(scored, policy_topic)
    return scored[:limit]


SKIN_TYPE_HINTS: dict[str, list[str]] = {
    "oily": ["niacinamide", "salicylic", "gel", "lightweight", "pore", "oil-control"],
    "dry": ["ceramide", "barrier", "cream", "hydrat", "repair", "rich"],
    "combination": ["balance", "gel", "niacinamide", "lightweight"],
    "sensitive": ["fragrance-free", "gentle", "mineral", "barrier", "soothing"],
    "normal": ["daily", "hydrat", "maintain"],
}

PRODUCT_TYPE_HINTS: dict[str, list[str]] = {
    "cleanser": ["cleanser", "foam", "wash"],
    "moisturizer": ["moistur", "hydrat", "cream"],
    "serum": ["serum"],
    "sunscreen": ["spf", "sunscreen"],
    "routine": ["cleanser", "serum", "moistur", "sunscreen"],
}


def _keyword_terms(query: str, profile: dict[str, Any] | None = None) -> set[str]:
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    profile = profile or {}

    for skin_type, hints in SKIN_TYPE_HINTS.items():
        if _contains_phrase(query, skin_type):
            terms.update(hints)

    for product_type, hints in PRODUCT_TYPE_HINTS.items():
        if _contains_phrase(query, product_type):
            terms.update(hints)

    for concern, config in CONCERN_SIGNALS.items():
        if any(term in query.lower() for term in config["match"]):
            terms.update(config["ingredients"])
            terms.update(config["tags"])

    if profile.get("skin_type"):
        terms.update(SKIN_TYPE_HINTS.get(str(profile["skin_type"]).lower(), []))

    for concern in detect_concerns(query, profile):
        config = CONCERN_SIGNALS.get(concern, {})
        terms.update(config.get("ingredients", []))
        terms.update(config.get("tags", []))

    return terms


def _concern_score(product: Product, concerns: list[str]) -> float:
    if not concerns:
        return 0.0

    haystack = _product_haystack(product)
    score = 0.0
    for concern in concerns:
        config = CONCERN_SIGNALS.get(concern, {})
        ingredient_hits = sum(1 for term in config.get("ingredients", []) if term in haystack)
        tag_hits = sum(1 for term in config.get("tags", []) if term in haystack)
        score += ingredient_hits * 2.5 + tag_hits * 2.0

        preferred_types = config.get("preferred_types", [])
        if preferred_types:
            if any(_product_matches_type(product, product_type) for product_type in preferred_types):
                score += 8.0
            elif _product_matches_type(product, "moisturizer") and concern == "acne":
                score -= 4.0

    return score


def pick_products_for_concerns(
    products: list[Product],
    concerns: list[str],
    limit: int = 3,
) -> list[Product]:
    if not products or not concerns:
        return products[:limit]

    primary = concerns[0]
    config = CONCERN_SIGNALS.get(primary, {})
    preferred_types = config.get("preferred_types", [])
    picks: list[Product] = []
    seen_ids: set[int] = set()

    ranked = sorted(products, key=lambda product: _concern_score(product, concerns), reverse=True)

    for product_type in preferred_types:
        for product in ranked:
            if product.id in seen_ids:
                continue
            if _product_matches_type(product, product_type):
                picks.append(product)
                seen_ids.add(product.id)
                break
        if len(picks) >= limit:
            return picks[:limit]

    for product in ranked:
        if product.id in seen_ids:
            continue
        picks.append(product)
        seen_ids.add(product.id)
        if len(picks) >= limit:
            break

    return picks


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


def search_products(
    db: Session,
    query: str,
    store_id: int,
    limit: int | None = None,
    profile: dict[str, Any] | None = None,
    enforce_product_type: bool = True,
) -> list[Product]:
    limit = limit or settings.PRODUCT_TOP_K
    products = (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.available.is_(True))
        .all()
    )
    if not products:
        return []

    retrieval_query = build_retrieval_query(query, profile=profile)
    query_terms = _keyword_terms(retrieval_query, profile=profile)
    query_vector = generate_embeddings([retrieval_query])[0]

    product_embeddings = [
        record
        for record in db.query(EmbeddingRecord).filter(EmbeddingRecord.store_id == store_id).all()
        if (record.meta or {}).get("type") == "product"
    ]
    semantic_by_product_id = {
        (record.meta or {}).get("product_id"): _cosine_similarity(query_vector, record.vector)
        for record in product_embeddings
    }

    requested_types = detect_requested_product_types(retrieval_query)

    active_concerns = detect_concerns(retrieval_query, profile)

    def score_product(product: Product) -> float:
        haystack = _product_haystack(product)
        keyword_score = sum(1 for term in query_terms if term in haystack)
        semantic_score = semantic_by_product_id.get(product.id, 0.0) * 10
        profile_bonus = 0.0
        if profile and profile.get("skin_type"):
            skin_type = str(profile["skin_type"]).lower()
            if skin_type in haystack:
                profile_bonus += 2.0
        for concern in (profile or {}).get("concerns", []):
            if str(concern).lower() in haystack:
                profile_bonus += 1.5

        concern_bonus = _concern_score(product, active_concerns)

        type_bonus = 0.0
        if requested_types:
            if any(_product_matches_type(product, product_type) for product_type in requested_types):
                type_bonus += 10.0
            else:
                type_bonus -= 8.0

        budget_bonus = 0.0
        if profile and profile.get("budget") == "budget-friendly":
            amount = _parse_price_amount(product.price)
            if amount is not None:
                if amount <= 2000:
                    budget_bonus += 3.0
                elif amount >= 3500:
                    budget_bonus -= 2.0

        return keyword_score + semantic_score + profile_bonus + concern_bonus + type_bonus + budget_bonus

    ranked = sorted(products, key=score_product, reverse=True)
    if requested_types and enforce_product_type:
        typed = [product for product in ranked if any(_product_matches_type(product, t) for t in requested_types)]
        if typed:
            return typed[:limit]
    top = [product for product in ranked if score_product(product) > 0]
    return (top or ranked)[:limit]
