from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import DB
from app.models.game import GameState
from app.routers.admin.deps import verify_admin
from app.schemas.game import TimeIn, TimeOut

router = APIRouter(prefix="/time", tags=["admin: /time"], dependencies=[Depends(verify_admin)])


def _timeout(game: GameState, message: str) -> TimeOut:
    return TimeOut(
        message=message,
        start_at=game.start_at,
        end_at=game.end_at,
        paused_until=game.paused_until,
    )


@router.post("/start", response_model=TimeOut, summary="Change start time")
async def change_start_time(body: TimeIn, db: DB) -> TimeOut:
    game = await db.scalar(select(GameState))
    if not game:
        game = GameState(
            start_at=body.time,
            end_at=body.time + timedelta(hours=2),
            paused_until=body.time,
        )
        db.add(game)
    else:
        if body.time >= game.end_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be less than end time",
            )
        game.start_at = body.time

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
    if body.time <= game.start_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be greater than start time",
        )

    game.end_at = body.time
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
    if not (game.start_at <= body.time <= game.end_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pause time must be between start and end time",
        )

    game.paused_until = body.time
    await db.commit()
    return _timeout(game, "Pause time updated successfully")
