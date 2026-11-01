from datetime import UTC
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.clock import utcnow
from app.core.cookies import ADMIN_COOKIE
from app.deps import DB
from app.models.game import GameState
from app.verify.admin import verify_admin_payload
from app.verify.token import verify_access_token

security = HTTPBearer(auto_error=False)


def get_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract admin JWT token from HttpOnly cookie or Authorization Bearer header."""
    token = request.cookies.get(ADMIN_COOKIE) or request.cookies.get("access_token")
    if token:
        return token
    if credentials and credentials.credentials:
        return credentials.credentials
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def verify_admin(db: DB, token: str = Depends(get_admin_token)) -> None:
    """Verify admin JWT payload."""
    payload = verify_access_token(token)
    await verify_admin_payload(payload, db)


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
