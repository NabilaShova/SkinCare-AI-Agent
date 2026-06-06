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

    blocks = [re.sub(r"[ \t]+", " ", block.strip()) for block in re.split(r"\n\s*\n", normalized)]
    blocks = [block for block in blocks if block]
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

    recent_user_messages = [item["content"] for item in history[-4:] if item["role"] == "user"]
    if len(recent_user_messages) > 1:
        parts.append("recent context: " + " | ".join(recent_user_messages[:-1]))

    return ". ".join(part for part in parts if part)


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
    "policy": ["shipping", "return", "store-faq"],
    "faq": ["store-faq"],
}

INGREDIENT_SOURCE_HINTS: dict[str, list[str]] = {
    "niacinamide": ["ingredient"],
    "vitamin c": ["ingredient"],
    "retinol": ["ingredient"],
    "salicylic": ["ingredient"],
    "hyaluronic": ["ingredient"],
    "ceramide": ["ingredient"],
    "ingredient": ["ingredient"],
    "layer": ["ingredient", "product-usage"],
    "routine": ["product-usage", "skin-consultation"],
}


def _source_boost(query: str, source: str, intent: str | None = None) -> float:
    lowered_query = query.lower()
    lowered_source = source.lower()
    boost = 0.0
    hint_map = POLICY_SOURCE_HINTS if intent == "policy_faq" else INGREDIENT_SOURCE_HINTS if intent == "ingredient_question" else {}

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
            + _source_boost(query, (record.meta or {}).get("source", ""), intent=intent)
            + _keyword_overlap_boost(query, record.chunk_text),
        }
        for record in records
    ]
    scored = [item for item in scored if item["score"] >= settings.RAG_MIN_SCORE]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


PROFILE_HINTS: dict[str, list[str]] = {
    "oily": ["oil", "niacinamide", "salicylic", "gel", "acne", "pore"],
    "dry": ["ceramide", "barrier", "cream", "hydrat", "repair"],
    "combination": ["balance", "gel", "niacinamide", "lightweight"],
    "sensitive": ["fragrance-free", "gentle", "mineral", "barrier", "soothing"],
    "normal": ["daily", "hydrat", "maintain"],
    "acne": ["salicylic", "niacinamide", "bha", "acne", "clarify"],
    "hyperpigmentation": ["vitamin c", "bright", "tone", "dark spot"],
    "dark spots": ["vitamin c", "bright", "tone", "dark spot"],
    "fine lines": ["retinol", "peptide", "renewal", "anti-aging"],
    "wrinkles": ["retinol", "peptide", "renewal", "anti-aging"],
    "redness": ["niacinamide", "soothing", "barrier", "gentle"],
    "dehydration": ["hyaluronic", "hydrat", "ceramide"],
    "uneven skin tone": ["vitamin c", "bright", "tone"],
    "enlarged pores": ["niacinamide", "salicylic", "pore"],
    "brightening": ["vitamin c", "bright", "tone"],
    "aging": ["retinol", "peptide", "line", "renewal"],
    "sun protection": ["spf", "sunscreen", "mineral"],
    "cleanser": ["cleanser", "foam", "wash"],
    "moisturizer": ["moistur", "hydrat", "cream", "gel"],
    "serum": ["serum"],
    "sunscreen": ["spf", "sunscreen"],
    "routine": ["cleanser", "serum", "moistur", "sunscreen"],
}


def _keyword_terms(query: str, profile: dict[str, Any] | None = None) -> set[str]:
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    profile = profile or {}

    for key, hints in PROFILE_HINTS.items():
        if key in query.lower():
            terms.update(hints)

    if profile.get("skin_type"):
        terms.update(PROFILE_HINTS.get(str(profile["skin_type"]).lower(), []))
    for concern in profile.get("concerns", []):
        terms.update(PROFILE_HINTS.get(str(concern).lower(), []))

    return terms


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

    def score_product(product: Product) -> float:
        keyword_score = sum(1 for term in query_terms if term in _product_haystack(product))
        semantic_score = semantic_by_product_id.get(product.id, 0.0) * 10
        profile_bonus = 0.0
        if profile and profile.get("skin_type"):
            skin_type = str(profile["skin_type"]).lower()
            if skin_type in _product_haystack(product):
                profile_bonus += 2.0
        for concern in (profile or {}).get("concerns", []):
            if str(concern).lower() in _product_haystack(product):
                profile_bonus += 1.5
        return keyword_score + semantic_score + profile_bonus

    ranked = sorted(products, key=score_product, reverse=True)
    top = [product for product in ranked if score_product(product) > 0]
    return (top or ranked)[:limit]
