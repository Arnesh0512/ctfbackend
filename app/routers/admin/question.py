from decimal import Decimal
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import DB
from app.models.content import Path, Question
from app.routers.admin.deps import _assert_before_game_start, verify_admin
from app.schemas.question import (
    QuestionCreateIn,
    QuestionCreateOut,
    QuestionDeleteOut,
    QuestionDetailOut,
    QuestionSummaryOut,
    QuestionUpdateIn,
)
from app.services.storage import delete_files_from_supabase, extract_s3_object_path

router = APIRouter(prefix="/question", tags=["admin: /question"], dependencies=[Depends(verify_admin)])


def _format_location(state: str, monument: str) -> str:
    """Format location as <state-monument> with spaces and underscores replaced by '-'."""
    raw = f"{state.strip()}-{monument.strip()}"
    return re.sub(r"[\s_]+", "-", raw).strip("-")


@router.post(
    "",
    response_model=QuestionCreateOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question (Admin only)",
)
async def create_question(
    body: QuestionCreateIn,
    db: DB,
) -> QuestionCreateOut:
    """Create a new question with initialized default state (Requires Admin JWT)."""
    await _assert_before_game_start(db, action="create")

    new_question = Question(
        question_id=uuid.uuid4(),
        title=body.title,
        monument=body.monument,
        state=body.state,
        story=body.story,
        hint1=body.hint1,
        hint2=body.hint2,
        file_path=body.file_path if body.file_path else None,
        flag=body.flag,
        base_points=body.base_points,
        current_points=body.base_points,
        end_point=body.end_point,
        retries=body.retries,
        is_viewed=False,
        first_solved_at=None,
        first_solved_by_team_id=None,
        is_blocked=None,
        unlocked_by_team_id=None,
    )

    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)

    return QuestionCreateOut(question_id=new_question.question_id)


@router.get(
    "",
    response_model=list[QuestionSummaryOut],
    summary="Get all questions summary (Admin only)",
)
async def get_all_questions(
    db: DB,
) -> list[QuestionSummaryOut]:
    """Get all questions returning question_id, title, current_points, and formatted location."""
    questions = (await db.scalars(select(Question).order_by(Question.question_id))).all()
    return [
        QuestionSummaryOut(
            question_id=q.question_id,
            title=q.title,
            current_points=q.current_points,
            location=_format_location(q.state, q.monument),
        )
        for q in questions
    ]


@router.get(
    "/{question_id}",
    response_model=QuestionDetailOut,
    summary="Get full question details (Admin only)",
)
async def get_question(
    question_id: uuid.UUID,
    db: DB,
) -> QuestionDetailOut:
    """Get full question details by question ID."""
    question = await db.scalar(select(Question).where(Question.question_id == question_id))
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{question_id}' not found.",
        )
    return QuestionDetailOut.model_validate(question)


@router.patch(
    "/{question_id}",
    response_model=QuestionDetailOut,
    summary="Update question mutable fields (Admin only)",
)
async def update_question(
    question_id: uuid.UUID,
    body: QuestionUpdateIn,
    db: DB,
) -> QuestionDetailOut:
    """Update allowed fields of a question before game start."""
    await _assert_before_game_start(db, action="update")

    question = await db.scalar(select(Question).where(Question.question_id == question_id))
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{question_id}' not found.",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(question, field, val)

    if "base_points" in update_data and update_data["base_points"] is not None:
        question.current_points = update_data["base_points"]

    await db.commit()
    await db.refresh(question)

    return QuestionDetailOut.model_validate(question)


@router.delete(
    "/{question_id}",
    response_model=QuestionDeleteOut,
    summary="Delete a question and its storage files in S3 (Admin only)",
)
async def delete_question(
    question_id: uuid.UUID,
    db: DB,
) -> QuestionDeleteOut:
    """Delete question from database and cascadingly delete its S3 files in monuments bucket."""
    await _assert_before_game_start(db, action="delete")

    question = await db.scalar(select(Question).where(Question.question_id == question_id))
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{question_id}' not found.",
        )

    # Clean up referenced storage files in Supabase monuments S3 bucket
    if question.file_path:
        s3_paths = [
            path
            for url in question.file_path
            if (path := extract_s3_object_path(url)) is not None
        ]
        if s3_paths:
            await delete_files_from_supabase(list(set(s3_paths)))

    # Also clean up from paths.questions if present
    paths = (await db.scalars(select(Path))).all()
    for p in paths:
        if p.questions and question_id in p.questions:
            p.questions = [qid for qid in p.questions if qid != question_id]

    await db.delete(question)
    await db.commit()

    return QuestionDeleteOut(
        message="Question and associated storage files deleted successfully.",
        question_id=question_id,
    )
