from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.clock import to_ist
from app.deps import DB
from app.models.game import GameState
from app.routers.admin.deps import verify_admin
from app.schemas.game import TimeIn, TimeOut

router = APIRouter(prefix="/time", tags=["admin: /time"], dependencies=[Depends(verify_admin)])


def _timeout(game: GameState, message: str) -> TimeOut:
    return TimeOut(
        message=message,
        start_at=to_ist(game.start_at),
        end_at=to_ist(game.end_at),
        paused_until=to_ist(game.paused_until),
    )


@router.post("/start", response_model=TimeOut, summary="Change start time")
async def change_start_time(body: TimeIn, db: DB) -> TimeOut:
    game = await db.scalar(select(GameState))
    target_time = to_ist(body.time)
    if not game:
        game = GameState(
            start_at=target_time,
            end_at=target_time + timedelta(hours=2),
            paused_until=target_time,
        )
        db.add(game)
    else:
        if target_time >= to_ist(game.end_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be less than end time",
            )
        game.start_at = target_time

    await db.commit()
    return _timeout(game, "Start time updated successfully")


@router.post("/end", response_model=TimeOut, summary="Change end time")
async def change_end_time(body: TimeIn, db: DB) -> TimeOut:
    game = await db.scalar(select(GameState))
    if not game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game has not been initialized yet",
        )
    target_time = to_ist(body.time)
    if target_time <= to_ist(game.start_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be greater than start time",
        )

    game.end_at = target_time
    await db.commit()
    return _timeout(game, "End time updated successfully")


@router.post("/pause", response_model=TimeOut, summary="Change pause time")
async def pause_game(body: TimeIn, db: DB) -> TimeOut:
    game = await db.scalar(select(GameState))
    if not game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game has not been initialized yet",
        )
    target_time = to_ist(body.time)
    if not (to_ist(game.start_at) <= target_time <= to_ist(game.end_at)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pause time must be between start and end time",
        )

    game.paused_until = target_time
    await db.commit()
    return _timeout(game, "Pause time updated successfully")
