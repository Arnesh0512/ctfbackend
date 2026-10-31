import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.team import Team


async def verify_team_username(
    username: str,
    db: AsyncSession,
    type: str = "N",
) -> Team | None:
    """Verify team existence or absence by username.

    type='N' (New): checks that username does not exist. Raises 409 if already taken.
    type='Y' (Yes/Must Exist): checks that team exists. Raises 404 if missing.
    """
    username = username.strip()
    team = await db.scalar(select(Team).where(Team.username == username))

    if type == "N" and team:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{username}' is already in use.",
        )

    if type == "Y" and not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return team


async def verify_team_by_id(
    team_id: uuid.UUID | str,
    db: AsyncSession,
    type: str = "Y",
) -> Team | None:
    """Verify team existence or absence by UUID.

    type='Y': team must exist, raises 404 if missing.
    type='N': team must not exist, raises 409 if exists.
    """
    if isinstance(team_id, str):
        try:
            team_id = uuid.UUID(team_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format for team_id",
            )

    team = await db.scalar(select(Team).where(Team.team_id == team_id))

    if type == "N" and team:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team already exists",
        )

    if type == "Y" and not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return team


async def verify_team_credentials(
    username: str,
    password: str,
    db: AsyncSession,
) -> Team:
    """Verify team login credentials against the database."""
    username = username.strip()
    team = await db.scalar(select(Team).where(Team.username == username))
    if not team:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid team credentials",
        )

    if not verify_password(password, team.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid team credentials",
        )

    return team


async def verify_team_payload(
    payload: dict[str, Any],
    db: AsyncSession,
) -> tuple[Team, uuid.UUID, str]:
    """Verify decoded JWT payload for team access."""
    team_id_raw = payload.get("team_id")
    role = payload.get("role")

    if not team_id_raw or role != "team":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload for team",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        team_id = uuid.UUID(str(team_id_raw))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid team identifier in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    team = await verify_team_by_id(team_id, db, type="Y")
    return team, team.team_id, team.username
