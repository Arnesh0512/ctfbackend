from datetime import UTC
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.clock import utcnow
from app.deps import DB
from app.models.content import Path, Question
from app.models.game import GameState
from app.routers.time import verify_admin
from app.schemas.path import (
    PathCreateIn,
    PathCreateOut,
    PathDeleteOut,
    PathQuestionItem,
    PathSummaryOut,
    PathUpdateIn,
)

router = APIRouter(prefix="/admin/path", tags=["admin: /path"], dependencies=[Depends(verify_admin)])


async def _assert_before_game_start(db: DB, action: str = "create") -> None:
    """Ensure paths cannot be created, updated, or deleted after game start."""
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


def _format_location(state: str, monument: str) -> str:
    """Format location as <state-monument> with spaces and underscores replaced by '-'."""
    raw = f"{state.strip()}-{monument.strip()}"
    return re.sub(r"[\s_]+", "-", raw).strip("-")


async def _get_path_summary(path: Path, db: DB) -> PathSummaryOut:
    """Build PathSummaryOut preserving the question ordering."""
    items: list[PathQuestionItem] = []
    if path.questions:
        questions = (
            await db.scalars(select(Question).where(Question.question_id.in_(path.questions)))
        ).all()
        q_map = {q.question_id: q for q in questions}
        items = [
            PathQuestionItem(
                question_id=qid,
                location=_format_location(q_map[qid].state, q_map[qid].monument),
            )
            for qid in path.questions
            if qid in q_map
        ]
    return PathSummaryOut(
        path_id=path.path_id,
        path_name=path.path_name,
        questions=items,
    )


@router.post(
    "",
    response_model=PathCreateOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new path (Admin only)",
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


@router.get(
    "",
    response_model=list[PathSummaryOut],
    summary="Get all paths (Admin only)",
)
async def get_all_paths(
    db: DB,
) -> list[PathSummaryOut]:
    """Get all paths with path_id, path_name, and ordered questions list with formatted location."""
    paths = (await db.scalars(select(Path).order_by(Path.path_name))).all()
    if not paths:
        return []

    # Batch-fetch all referenced questions across all paths
    all_qids = set()
    for p in paths:
        if p.questions:
            all_qids.update(p.questions)

    q_map = {}
    if all_qids:
        questions = (await db.scalars(select(Question).where(Question.question_id.in_(all_qids)))).all()
        q_map = {q.question_id: q for q in questions}

    results: list[PathSummaryOut] = []
    for p in paths:
        items = [
            PathQuestionItem(
                question_id=qid,
                location=_format_location(q_map[qid].state, q_map[qid].monument),
            )
            for qid in (p.questions or [])
            if qid in q_map
        ]
        results.append(
            PathSummaryOut(
                path_id=p.path_id,
                path_name=p.path_name,
                questions=items,
            )
        )

    return results


@router.patch(
    "/{path_id}",
    response_model=PathSummaryOut,
    summary="Update path mutable fields (Admin only)",
)
async def update_path(
    path_id: uuid.UUID,
    body: PathUpdateIn,
    db: DB,
) -> PathSummaryOut:
    """Update path name and/or questions before game start.

    Validations:
    1. Game must not have started yet.
    2. Path must exist.
    3. If path_name is provided, it must be unique across all other paths.
    4. If question_ids are provided:
       - No duplicates within request.
       - All question IDs must exist in the database.
       - None of the question IDs can belong to any other path record.
    """
    await _assert_before_game_start(db, action="update")

    path = await db.scalar(select(Path).where(Path.path_id == path_id))
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path '{path_id}' not found.",
        )

    # 1. Update path_name if provided
    if body.path_name is not None and body.path_name != path.path_name:
        existing_name = await db.scalar(
            select(Path).where(Path.path_name == body.path_name, Path.path_id != path_id)
        )
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path with name '{body.path_name}' already exists.",
            )
        path.path_name = body.path_name

    # 2. Update question_ids if provided
    if body.question_ids is not None:
        # Check all question IDs exist in DB
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

        # Check none of the question IDs are assigned to any OTHER path
        other_paths = (await db.scalars(select(Path).where(Path.path_id != path_id))).all()
        incoming_set = set(body.question_ids)
        for p in other_paths:
            if p.questions:
                overlap = incoming_set.intersection(set(p.questions))
                if overlap:
                    overlap_strs = [str(qid) for qid in overlap]
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Question IDs {overlap_strs} are already assigned to path '{p.path_name}'.",
                    )

        path.questions = body.question_ids

    await db.commit()
    await db.refresh(path)

    return await _get_path_summary(path, db)


@router.delete(
    "/{path_id}",
    response_model=PathDeleteOut,
    summary="Delete a path record (Admin only)",
)
async def delete_path(
    path_id: uuid.UUID,
    db: DB,
) -> PathDeleteOut:
    """Delete path record without deleting its questions."""
    await _assert_before_game_start(db, action="delete")

    path = await db.scalar(select(Path).where(Path.path_id == path_id))
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path '{path_id}' not found.",
        )

    # Just delete path record, do not delete questions
    await db.delete(path)
    await db.commit()

    return PathDeleteOut(
        message="Path deleted successfully.",
        path_id=path_id,
    )
