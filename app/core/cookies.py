from typing import Any

from fastapi import Response

from app.core.config import settings
from app.core.security import Role

TEAM_COOKIE = "team_token"
ADMIN_COOKIE = "admin_token"

_NAMES: dict[Role, str] = {
    "team": TEAM_COOKIE,
    "admin": ADMIN_COOKIE,
}


def _options(role: Role) -> dict[str, Any]:
    prefix = settings.api_prefix.rstrip("/")
    path = f"{prefix}/admin" if role == "admin" else (f"{prefix}/" if prefix else "/")
    return {
        "path": path,
        "secure": settings.cookie_secure,
        "httponly": True,
        "samesite": "strict",
    }


def set_auth_cookie(response: Response, role: Role, token: str) -> None:
    """Set JWT as an HttpOnly secure cookie so it cannot be viewed or accessed via JavaScript."""
    response.set_cookie(
        _NAMES[role],
        token,
        max_age=settings.token_ttl_seconds,
        **_options(role),
    )


def clear_auth_cookie(response: Response, role: Role) -> None:
    """Delete the authentication cookie using matching path and flags."""
    response.delete_cookie(
        _NAMES[role],
        **_options(role)
    )
