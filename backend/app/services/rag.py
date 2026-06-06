import math
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EmbeddingRecord, Product


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
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


def search_knowledge(
    db: Session,
    query: str,
    store_id: int,
    limit: int | None = None,
    include_products: bool = False,
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
            "score": _cosine_similarity(query_vector, record.vector),
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
