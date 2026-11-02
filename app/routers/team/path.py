from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import DB
from app.models.content import Path
from app.models.team import Team
from app.routers.team.auth import get_current_team
from app.schemas.path import TeamCurrentPathOut, TeamPathOut
from app.schemas.team import TeamOut

router = APIRouter(prefix="/path", tags=["teams: /path"])


@router.get("", response_model=list[TeamPathOut], summary="Get all paths (Public, No JWT)")
async def get_team_paths(db: DB) -> list[TeamPathOut]:
    """
    Fetch all paths and return a list of dictionaries containing path_id
    and the first member of questions (question_id). No JWT authentication required.
    """
    paths = (await db.scalars(select(Path).order_by(Path.path_name.asc()))).all()
    return [
        TeamPathOut(
            path_id=p.path_id,
            question_id=p.questions[0] if (p.questions and len(p.questions) > 0) else None,
        )
        for p in paths
    ]


@router.get("/current", response_model=TeamCurrentPathOut, summary="Get current path for team")
async def get_current_team_path(
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamCurrentPathOut:
    """Fetch the current_path_id for the authenticated team (Requires Team JWT)."""
    team = await db.get(Team, current_team.team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )
    return TeamCurrentPathOut(current_path_id=team.current_path_id)
