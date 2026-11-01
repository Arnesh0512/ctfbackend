from fastapi import APIRouter
from sqlalchemy import select

from app.core.clock import utcnow
from app.deps import DB
from app.models.game import GameState
from app.schemas.game import GameStateOut

router = APIRouter(tags=["game"])


@router.get("/game/state", response_model=GameStateOut, summary="Get Game State")
@router.get("/state", response_model=GameStateOut, summary="Get Game State (Alias)")
async def get_game_state(db: DB) -> GameStateOut:
    """Check game state against current UTC time:

    - ACTIVE: Game has started and is currently ongoing (start_at <= now < end_at).
    - PAUSED: Game is temporarily frozen (now < paused_until).
    - PASSIVE: Game has not started yet (now < start_at) or has concluded (now >= end_at).

    Public endpoint: No JWT authentication required.
    """
    stmt = select(GameState).order_by(GameState.start_at.desc()).limit(1)
    game = await db.scalar(stmt)

    if not game:
        return GameStateOut(
            message="PASSIVE",
            status="PASSIVE",
        )

    now = utcnow()

    # 1. Check if game is currently paused
    if game.paused_until and now < game.paused_until:
        return GameStateOut(
            message="PAUSED",
            status="PAUSED",
            start_at=game.start_at,
            end_at=game.end_at,
            paused_until=game.paused_until,
        )

    # 2. Check if game is active
    if game.start_at <= now < game.end_at:
        return GameStateOut(
            message="ACTIVE",
            status="ACTIVE",
            start_at=game.start_at,
            end_at=game.end_at,
            paused_until=game.paused_until,
        )

    # 3. Otherwise (before start_at or after end_at) -> PASSIVE
    return GameStateOut(
        message="PASSIVE",
        status="PASSIVE",
        start_at=game.start_at,
        end_at=game.end_at,
        paused_until=game.paused_until,
    )
