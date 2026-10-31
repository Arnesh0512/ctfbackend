from datetime import timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.clock import utcnow
from app.core.config import settings


def create_access_token(payload_data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    now = utcnow()
    expire = now + (expires_delta or timedelta(seconds=settings.token_ttl_seconds))
    to_encode = {**payload_data, "iat": now, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp"]},
        )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
