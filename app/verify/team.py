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
) -> None:
    """Verify that the team username is not already taken."""
    username = username.strip()
    existing = await db.scalar(select(Team).where(Team.username == username))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{username}' is already in use.",
        )


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
    """Verify that decoded token payload represents a valid active team in database."""
    role = payload.get("role")
    team_id_raw = payload.get("team_id")

    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if role != "team":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Team privilege required",
        )

    if not team_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing team identifier in token",
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

    team = await db.scalar(select(Team).where(Team.team_id == team_id))
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return team, team.team_id, team.username
