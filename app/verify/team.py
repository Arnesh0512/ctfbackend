from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
