from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import DB
from app.models.team import Team
from app.routers.team.auth import get_current_team
from app.schemas.question import TeamCurrentQuestionOut
from app.schemas.team import TeamOut

router = APIRouter(prefix="/question", tags=["teams: /question"])


@router.get("/current", response_model=TeamCurrentQuestionOut, summary="Get current question for team")
async def get_current_team_question(
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamCurrentQuestionOut:
    """Fetch current_question_id and current_path_id for the authenticated team (Requires Team JWT)."""
    team = await db.get(Team, current_team.team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )
    return TeamCurrentQuestionOut(
        current_question_id=team.current_question_id,
        current_path_id=team.current_path_id,
    )
