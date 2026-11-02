from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB
from app.models.content import Path
from app.schemas.path import TeamPathOut

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
