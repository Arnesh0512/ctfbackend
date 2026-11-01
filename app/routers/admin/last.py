import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import DB
from app.models.content import Path, Question
from app.models.game import GameState
from app.routers.admin.deps import _assert_before_game_start, verify_admin
from app.schemas.last import LastQuestionIn, LastQuestionOut
from app.schemas.question import QuestionDetailOut

router = APIRouter(prefix="/last", tags=["admin: /last"], dependencies=[Depends(verify_admin)])


@router.post(
    "",
    response_model=LastQuestionOut,
    status_code=status.HTTP_200_OK,
    summary="Set or clear the last question (Admin only)",
)
async def set_last_question(
    db: DB,
    body: LastQuestionIn | None = None,
) -> LastQuestionOut:
    """Set or clear the final question for the game.

    Checks:
    1. Game has not started yet.
    2. If question_id is provided:
       - Must exist in the questions table.
       - Must not be present in any list of question_ids in any row of the paths table.
       - Place this question in the 'last' field of game_state (replaces existing value).
    3. If question_id is null / omitted:
       - Simply clear 'last' field in game_state (set to null).
    """
    await _assert_before_game_start(db, action="modify last question")

    target_qid = body.question_id if body else None

    game = await db.scalar(select(GameState))
    if not game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game state has not been initialized. Please create game start and end time first.",
        )

    if target_qid is None:
        game.last = None
        await db.commit()
        await db.refresh(game)
        return LastQuestionOut(
            message="Last question cleared successfully",
            question_id=None,
            last=None,
        )

    # 1. Check question exists in db
    question = await db.scalar(select(Question).where(Question.question_id == target_qid))
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{target_qid}' does not exist.",
        )

    # 2. Check question is not in any row of paths table
    paths = (await db.scalars(select(Path))).all()
    for p in paths:
        if p.questions and target_qid in p.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question with ID '{target_qid}' is already present in path '{p.path_name}'.",
            )

    # 3. Store in last field (replaces previous value if present)
    game.last = target_qid
    await db.commit()
    await db.refresh(game)

    return LastQuestionOut(
        message="Last question updated successfully",
        question_id=game.last,
        last=game.last,
    )


@router.get(
    "",
    response_model=QuestionDetailOut,
    summary="Get complete details of the last question (Admin only)",
)
async def get_last_question(
    db: DB,
) -> QuestionDetailOut:
    """Send admin the complete question details for the question configured in game_state.last."""
    game = await db.scalar(select(GameState))
    if not game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game state has not been initialized. Please create game start and end time first.",
        )
    if not game.last:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No last question is currently configured.",
        )

    question = await db.scalar(select(Question).where(Question.question_id == game.last))
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Last question '{game.last}' not found in the database.",
        )

    return QuestionDetailOut.model_validate(question)
