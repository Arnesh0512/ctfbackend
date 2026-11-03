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

    is_paused = False
    if game and game.pause_start_at:
        p_start = to_ist(game.pause_start_at)
        p_end = to_ist(game.pause_end_at) if game.pause_end_at else None
        if p_end:
            is_paused = (p_start <= now <= p_end)
        else:
            is_paused = (now >= p_start)

    if is_paused:
        message = "PAUSED"
    elif game and to_ist(game.start_at) <= now < to_ist(game.end_at):
        message = "ACTIVE"
    else:
        message = "PASSIVE"

    return GameStateOut(
        message=message,
        start_at=to_ist(game.start_at) if game else None,
        end_at=to_ist(game.end_at) if game else None,
        pause_start_at=to_ist(game.pause_start_at) if game and game.pause_start_at else None,
        pause_end_at=to_ist(game.pause_end_at) if game and game.pause_end_at else None,
        last=game.last if game else None,
    )
