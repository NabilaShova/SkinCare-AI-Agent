from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt

from app.core.config import settings

admin_api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)


def create_admin_token(store_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": "admin", "store_id": store_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_admin_api_key(api_key: str | None) -> None:
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API key")


def verify_admin_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token") from exc


def require_admin(api_key: str | None = Security(admin_api_key_header)) -> None:
    if settings.ENVIRONMENT == "development" and not api_key:
        return
    verify_admin_api_key(api_key)
