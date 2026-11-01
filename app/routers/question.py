from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, status

from app.deps import DB
from app.models.content import Question
from app.routers.time import verify_admin
from app.schemas.question import QuestionCreateIn, QuestionCreateOut

router = APIRouter(prefix="/question", tags=["question"], dependencies=[Depends(verify_admin)])


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
        decay_rate=Decimal("0.00"),
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
