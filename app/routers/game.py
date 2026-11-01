from fastapi import APIRouter
from sqlalchemy import select

from app.core.clock import utcnow
from app.deps import DB
from app.models.game import GameState
from app.schemas.game import GameStateOut

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/state", response_model=GameStateOut, summary="Get Game State")
async def get_state(db: DB) -> GameStateOut:
    game = await db.scalar(select(GameState))
    now = utcnow()

    if game and game.paused_until and now < game.paused_until:
        return GameStateOut(message="PAUSED")
    if game and game.start_at <= now < game.end_at:
        return GameStateOut(message="ACTIVE")
    return GameStateOut(message="PASSIVE")
