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


def search_knowledge(db: Session, query: str, store_id: int, limit: int = 4) -> list[dict[str, Any]]:
    records = (
        db.query(EmbeddingRecord)
        .filter(EmbeddingRecord.store_id == store_id)
        .all()
    )
    if not records:
        return []

    query_vector = generate_embeddings([query])[0]
    scored = [
        {
            "text": record.chunk_text,
            "source": (record.meta or {}).get("source", "knowledge-base"),
            "score": _cosine_similarity(query_vector, record.vector),
        }
        for record in records
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def search_products(db: Session, query: str, store_id: int, limit: int = 5) -> list[Product]:
    products = (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.available.is_(True))
        .all()
    )
    if not products:
        return []

    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    skin_terms = {
        "oily": ["oil", "niacinamide", "salicylic", "gel", "acne"],
        "dry": ["ceramide", "barrier", "cream", "hydrat"],
        "acne": ["salicylic", "niacinamide", "bha", "acne"],
        "sensitive": ["fragrance", "mineral", "gentle", "barrier"],
        "bright": ["vitamin c", "bright", "tone"],
        "aging": ["retinol", "peptide", "line", "renewal"],
        "sun": ["spf", "sunscreen", "mineral"],
    }

    for term, hints in skin_terms.items():
        if term in query.lower():
            query_terms.update(hints)

    def score_product(product: Product) -> int:
        haystack = " ".join(
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
        return sum(1 for term in query_terms if term in haystack)

    ranked = sorted(products, key=score_product, reverse=True)
    top = [product for product in ranked if score_product(product) > 0]
    return (top or ranked)[:limit]
