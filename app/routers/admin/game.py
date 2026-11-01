from fastapi import APIRouter
from sqlalchemy import select

from app.core.clock import utcnow
from app.deps import DB
from app.models.game import GameState
from app.schemas.game import GameStateOut

router = APIRouter(prefix="/game", tags=["admin: /game"])


@router.get("/state", response_model=GameStateOut, summary="Get Game State")
async def get_state(db: DB) -> GameStateOut:
    """Fetch current game state."""
    game = await db.scalar(select(GameState))
    now = utcnow()

    if game and game.paused_until and now < game.paused_until:
        message = "PAUSED"
    elif game and game.start_at <= now < game.end_at:
        message = "ACTIVE"
    else:
        message = "PASSIVE"

    return GameStateOut(
        message=message,
        start_at=game.start_at if game else None,
        end_at=game.end_at if game else None,
    )
