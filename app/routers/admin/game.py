from fastapi import APIRouter
from sqlalchemy import select

from app.core.clock import istnow, to_ist
from app.deps import DB
from app.models.game import GameState
from app.schemas.game import GameStateOut

router = APIRouter(prefix="/game", tags=["admin: /game"])


@router.get("/state", response_model=GameStateOut, summary="Get Game State")
async def get_state(db: DB) -> GameStateOut:
    """Fetch current game state."""
    game = await db.scalar(select(GameState))
    now = istnow()

    if game and game.paused_until and now < to_ist(game.paused_until):
        message = "PAUSED"
    elif game and to_ist(game.start_at) <= now < to_ist(game.end_at):
        message = "ACTIVE"
    else:
        message = "PASSIVE"

    return GameStateOut(
        message=message,
        start_at=to_ist(game.start_at) if game else None,
        end_at=to_ist(game.end_at) if game else None,
        paused_until=to_ist(game.paused_until) if game else None,
        last=game.last if game else None,
    )
