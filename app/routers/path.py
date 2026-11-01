from datetime import UTC
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.clock import utcnow
from app.deps import DB
from app.models.content import Path, Question
from app.models.game import GameState
from app.routers.time import verify_admin
from app.schemas.path import PathCreateIn, PathCreateOut

router = APIRouter(prefix="/path", tags=["path"], dependencies=[Depends(verify_admin)])


async def _assert_before_game_start(db: DB, action: str = "create") -> None:
    """Ensure paths cannot be created or modified after game start."""
    game = await db.scalar(select(GameState))
    if game:
        start_at = game.start_at
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=UTC)
        if utcnow() >= start_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot {action} paths after the game has started.",
            )


@router.post(
    "",
    response_model=PathCreateOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new path (Admin only)",
)
@router.post(
    "s",
    response_model=PathCreateOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_path(
    body: PathCreateIn,
    db: DB,
) -> PathCreateOut:
    """Create a new path in the paths table.

    Validations:
    1. Game must not have started yet.
    2. path_name must be unique across paths table.
    3. question_ids must not contain duplicates within the request.
    4. question_ids must not overlap with questions in any existing path.
    5. All question_ids must exist in the questions database table.
    """
    await _assert_before_game_start(db, action="create")

    # 1. Check path_name uniqueness
    existing_name = await db.scalar(select(Path).where(Path.path_name == body.path_name))
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path with name '{body.path_name}' already exists.",
        )

    # 2. Check all question_ids exist in database
    existing_qids_res = await db.scalars(
        select(Question.question_id).where(Question.question_id.in_(body.question_ids))
    )
    found_qids = set(existing_qids_res.all())
    missing_qids = set(body.question_ids) - found_qids
    if missing_qids:
        missing_strs = [str(qid) for qid in missing_qids]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question IDs not found in database: {missing_strs}",
        )

    # 3. Check none of the question_ids are present in another record in paths table
    existing_paths = (await db.scalars(select(Path))).all()
    incoming_set = set(body.question_ids)
    for p in existing_paths:
        if p.questions:
            overlap = incoming_set.intersection(set(p.questions))
            if overlap:
                overlap_strs = [str(qid) for qid in overlap]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Question IDs {overlap_strs} are already assigned to path '{p.path_name}'.",
                )

    # 4. Create and store new path
    new_path = Path(
        path_id=uuid.uuid4(),
        path_name=body.path_name,
        questions=body.question_ids,
    )
    db.add(new_path)
    await db.commit()
    await db.refresh(new_path)

    return PathCreateOut(path_id=new_path.path_id)
