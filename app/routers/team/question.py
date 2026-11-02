from decimal import Decimal
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update

from app.core.calculate import calculate_question_points
from app.core.clock import utcnow
from app.core.events import broadcaster
from app.core.time import validate_frontend_timestamp
from app.deps import DB
from app.models.content import Path, Question
from app.models.enums import QuestionEvent
from app.models.game import GameState
from app.models.logs import TeamLog
from app.models.team import Team
from app.routers.team.auth import get_current_team
from app.schemas.question import (
    TeamCurrentQuestionOut,
    TeamQuestionSaveIn,
    TeamQuestionSaveOut,
    TeamQuestionViewIn,
    TeamQuestionViewOut,
)
from app.schemas.team import TeamOut

router = APIRouter(prefix="/question", tags=["teams: /question"])


@router.get("/current", response_model=TeamCurrentQuestionOut, summary="Get current question for team")
async def get_current_team_question(
    current_team: TeamOut = Depends(get_current_team),
) -> TeamCurrentQuestionOut:
    """Fetch current_question_id and current_path_id for the authenticated team (Requires Team JWT)."""
    return TeamCurrentQuestionOut(
        current_question_id=current_team.current_question_id,
        current_path_id=current_team.current_path_id,
    )


@router.post("/{question_id}", response_model=TeamQuestionViewOut, summary="View a question")
async def view_question(
    question_id: uuid.UUID,
    body: TeamQuestionViewIn,
    request: Request,
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamQuestionViewOut:
    """
    View question details (Requires Team JWT):
    1. Validates frontend_timestamp against game clock and freeze state.
    2. Validates question and path against team's progress.
    3. Inserts a VIEW event in team_logs with team's current points.
    4. If question is viewed for the first time, sets is_viewed and broadcasts via SSE.
    5. Returns allowed question details.
    """
    game_state = await db.scalar(select(GameState))
    if not game_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game state not found.")

    path_obj = await db.get(Path, body.path_id)
    if not path_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found.")

    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    # Step 1: Validate frontend timestamp
    backend_timestamp = getattr(request.state, "received_at", None) or utcnow()
    validate_frontend_timestamp(
        frontend_timestamp=body.frontend_timestamp,
        backend_timestamp=backend_timestamp,
        start_at=game_state.start_at,
        end_at=game_state.end_at,
        paused_until=game_state.paused_until,
        frozen_until=current_team.frozen_until,
    )

    # Step 2: Path & question validation
    if current_team.current_question_id is None and current_team.current_path_id is None:
        if not path_obj.questions or question_id != path_obj.questions[0]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong question")
    else:
        if current_team.current_question_id != question_id or current_team.current_path_id != body.path_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong question")

    # Step 3: Insert team_logs with event_type VIEW and team.points
    new_log = TeamLog(
        team_id=current_team.team_id,
        question_id=question_id,
        path_id=body.path_id,
        event_type=QuestionEvent.VIEW,
        created_at=body.frontend_timestamp,
        points=current_team.points,
    )
    db.add(new_log)

    # Step 4: First view check + SSE broadcast
    if question.is_viewed is None:
        question.is_viewed = body.frontend_timestamp
        await broadcaster.broadcast(
            event="question_first_viewed",
            data={
                "question_id": str(question_id),
                "base_points": float(question.base_points),
                "is_viewed": question.is_viewed.isoformat(),
                "start_at": game_state.start_at.isoformat(),
            },
        )

    await db.commit()
    await db.refresh(question)

    # Step 5: Return question details
    return TeamQuestionViewOut.model_validate(question)


@router.post("/save/{question_id}", response_model=TeamQuestionSaveOut, summary="Submit answer for a question")
async def save_question(
    question_id: uuid.UUID,
    body: TeamQuestionSaveIn,
    request: Request,
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamQuestionSaveOut:
    """
    Submit answer for a question (Requires Team JWT):
    1. Validates frontend_timestamp against game clock and freeze state.
    2. Validates question & path against team state (if null, logs START and locks team path/question).
    3. Checks retry count limit.
    4. Checks question block state.
    5. Evaluates answer:
       - Correct: calculates points, adds to team points, logs ANSWER_CORRECT, advances or marks reached Delhi.
       - Wrong: logs ANSWER_WRONG and returns error message with remaining retries.
    """
    game_state = await db.scalar(select(GameState))
    if not game_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game state not found.")

    path_obj = await db.get(Path, body.path_id)
    if not path_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found.")

    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    # Step 1: Check timestamp
    backend_timestamp = getattr(request.state, "received_at", None) or utcnow()
    validate_frontend_timestamp(
        frontend_timestamp=body.frontend_timestamp,
        backend_timestamp=backend_timestamp,
        start_at=game_state.start_at,
        end_at=game_state.end_at,
        paused_until=game_state.paused_until,
        frozen_until=current_team.frozen_until,
    )

    # Step 2: Path & question validation + start logging
    is_unstarted = current_team.current_question_id is None and current_team.current_path_id is None
    if is_unstarted:
        if not path_obj.questions or question_id != path_obj.questions[0]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong question")

        # Log START event
        start_log = TeamLog(
            team_id=current_team.team_id,
            question_id=question_id,
            path_id=body.path_id,
            event_type=QuestionEvent.START,
            created_at=body.frontend_timestamp,
            points=current_team.points,
        )
        db.add(start_log)
    else:
        if current_team.current_question_id != question_id or current_team.current_path_id != body.path_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong question")

    # Step 3: Check retry count
    stmt = (
        select(
            func.count().filter(TeamLog.event_type == QuestionEvent.ANSWER_WRONG).label("wrong_count"),
            func.count().filter(TeamLog.event_type == QuestionEvent.RETRY_PURCHASED).label("retry_count"),
        )
        .where(
            TeamLog.team_id == current_team.team_id,
            TeamLog.question_id == question_id,
            TeamLog.path_id == body.path_id,
        )
    )
    counts = (await db.execute(stmt)).one()
    wrong_count = counts.wrong_count or 0
    retry_count = counts.retry_count or 0

    if wrong_count >= (question.retries + retry_count):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Out of retries")

    # Step 4: Check if question is blocked
    if (
        question.is_blocked is not None
        and body.frontend_timestamp < question.is_blocked
        and (question.unlocked_by_team_id is None or current_team.team_id not in question.unlocked_by_team_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question is blocked until {question.is_blocked.isoformat()}",
        )

    # Step 5: Answer evaluation (exact case-sensitive comparison)
    if body.answer != question.flag:
        # Wrong answer
        wrong_log = TeamLog(
            team_id=current_team.team_id,
            question_id=question_id,
            path_id=body.path_id,
            event_type=QuestionEvent.ANSWER_WRONG,
            created_at=body.frontend_timestamp,
            points=current_team.points,
        )
        db.add(wrong_log)
        if is_unstarted:
            await db.execute(
                update(Team)
                .where(Team.team_id == current_team.team_id)
                .values(current_question_id=question_id, current_path_id=body.path_id)
            )
        await db.commit()
        remaining = (question.retries + retry_count) - (wrong_count + 1)
        return TeamQuestionSaveOut(
            correct=False,
            message="Answer wrong",
            current_points=current_team.points,
            remaining_retries=max(0, remaining),
        )

    # Correct answer!
    calc_points = calculate_question_points(
        question.is_viewed,
        game_state.start_at,
        body.frontend_timestamp,
        question.base_points,
    )
    points = Decimal(str(calc_points)) if calc_points is not None else question.base_points
    new_points = current_team.points + points

    correct_log = TeamLog(
        team_id=current_team.team_id,
        question_id=question_id,
        path_id=body.path_id,
        event_type=QuestionEvent.ANSWER_CORRECT,
        created_at=body.frontend_timestamp,
        points=new_points,
    )
    db.add(correct_log)

    actions: list[dict[str, str]] = []
    if question.first_solved_at is None:
        question.first_solved_at = body.frontend_timestamp
        question.first_solved_by_team_id = current_team.team_id
        actions.append({"Enable": "Block"})

    idx = path_obj.questions.index(question_id)
    if idx + 1 < len(path_obj.questions):
        next_qid = path_obj.questions[idx + 1]
        team_updates: dict[str, Any] = {
            "points": new_points,
            "current_question_id": next_qid,
        }
        if is_unstarted:
            team_updates["current_path_id"] = body.path_id
        await db.execute(
            update(Team)
            .where(Team.team_id == current_team.team_id)
            .values(**team_updates)
        )
        await db.commit()
        return TeamQuestionSaveOut(
            correct=True,
            message="Answered correct",
            next_question_id=next_qid,
            has_reached_delhi=False,
            points_awarded=points,
            current_points=new_points,
            actions=actions,
        )
    else:
        # Reached Delhi!
        # NOTE: Do NOT set current_question_id as None (per user request!)
        end_log = TeamLog(
            team_id=current_team.team_id,
            question_id=question_id,
            path_id=body.path_id,
            event_type=QuestionEvent.END,
            created_at=body.frontend_timestamp,
            points=new_points,
        )
        db.add(end_log)
        actions.append({"enable": "path_change"})
        team_updates = {
            "points": new_points,
            "has_reached_delhi": body.frontend_timestamp,
        }
        if is_unstarted:
            team_updates["current_question_id"] = question_id
            team_updates["current_path_id"] = body.path_id
        await db.execute(
            update(Team)
            .where(Team.team_id == current_team.team_id)
            .values(**team_updates)
        )
        await db.commit()
        return TeamQuestionSaveOut(
            correct=True,
            message="Answered correct, you have reached Delhi!",
            next_question_id=None,
            has_reached_delhi=True,
            points_awarded=points,
            current_points=new_points,
            actions=actions,
        )
