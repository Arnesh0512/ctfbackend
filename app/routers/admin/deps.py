from datetime import UTC
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.clock import utcnow
from app.core.cookies import ADMIN_COOKIE
from app.core.supabase_auth import fetch_admin_from_postgrest
from app.deps import DB
from app.models.game import GameState

security = HTTPBearer(auto_error=False)


def get_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract admin JWT token from Authorization Bearer header or HttpOnly cookie."""
    if credentials and credentials.credentials:
        return credentials.credentials
    token = request.cookies.get(ADMIN_COOKIE) or request.cookies.get("access_token")
    if token:
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def verify_admin(token: str = Depends(get_admin_token)) -> dict[str, Any]:
    """Verify admin JWT against Supabase PostgREST (Option 1). Zero backend secret required."""
    admin_data = await fetch_admin_from_postgrest(token)
    if not admin_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privilege required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin_data


async def _assert_before_game_start(db: DB, action: str = "modify") -> None:
    """Ensure operations cannot occur after the game has started."""
    game = await db.scalar(select(GameState))
    if game:
        start_at = game.start_at
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=UTC)
        if utcnow() >= start_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot {action} after the game has started.",
            )
