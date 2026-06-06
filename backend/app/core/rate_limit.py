import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request, namespace: str) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"{namespace}:{client_ip}"


def enforce_rate_limit(request: Request, *, namespace: str, limit_per_minute: int) -> None:
    if settings.ENVIRONMENT == "development":
        return

    key = _client_key(request, namespace)
    now = time.time()
    window_start = now - 60
    bucket = _buckets[key]

    while bucket and bucket[0] < window_start:
        bucket.popleft()

    if len(bucket) >= limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again shortly.",
        )

    bucket.append(now)
