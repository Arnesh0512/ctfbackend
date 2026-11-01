from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update

from app.deps import DB
from app.models.game import GameState
from app.routers.admin import get_admin_token
from app.schemas.game import TimeIn, TimeOut
from app.verify.admin import verify_admin_payload
from app.verify.token import verify_access_token


async def verify_admin(db: DB, token: str = Depends(get_admin_token)) -> None:
    payload = verify_access_token(token)
    await verify_admin_payload(payload, db)


router = APIRouter(prefix="/time", tags=["time"], dependencies=[Depends(verify_admin)])


async def _get_or_create_game(db: DB, default_time) -> GameState:
    game = await db.scalar(select(GameState))
    if not game:
        game = GameState(
            start_at=default_time,
            end_at=default_time + timedelta(hours=2),
            paused_until=default_time,
        )
        db.add(game)
        await db.commit()
    return game


@router.post("/start", response_model=TimeOut, summary="Change start time")
async def change_start_time(body: TimeIn, db: DB) -> TimeOut:
    game = await _get_or_create_game(db, body.time)
    if body.time >= game.end_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be less than end time",
        )
    await db.execute(update(GameState).values(start_at=body.time))
    await db.commit()
    game = await db.scalar(select(GameState))
    return TimeOut(
        message="Start time updated successfully",
        start_at=game.start_at,
        end_at=game.end_at,
        paused_until=game.paused_until,
    )


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
    await db.execute(update(GameState).values(end_at=body.time))
    await db.commit()
    game = await db.scalar(select(GameState))
    return TimeOut(
        message="End time updated successfully",
        start_at=game.start_at,
        end_at=game.end_at,
        paused_until=game.paused_until,
    )


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
    await db.execute(update(GameState).values(paused_until=body.time))
    await db.commit()
    game = await db.scalar(select(GameState))
    return TimeOut(
        message="Pause time updated successfully",
        start_at=game.start_at,
        end_at=game.end_at,
        paused_until=game.paused_until,
    )
