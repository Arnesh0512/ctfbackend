from datetime import timedelta
from decimal import Decimal
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update

from app.core.calculate import (
    calculate_block_time,
    calculate_hint_value,
    calculate_question_points,
    calculate_retry_value,
)
from app.core.clock import istnow, to_ist, utcnow
from app.core.events import broadcaster
from app.core.time import validate_frontend_timestamp
from app.deps import DB
from app.models.content import Path, Question
from app.models.enums import QuestionEvent
from app.models.game import GameState, StorePrice
from app.models.logs import TeamLog
from app.models.team import Team
from app.routers.team.auth import get_current_team
from app.schemas.question import (
    HintType,
    TeamCurrentQuestionOut,
    TeamQuestionBlockIn,
    TeamQuestionBlockOut,
    TeamQuestionHintIn,
    TeamQuestionHintOut,
    TeamQuestionRetryIn,
    TeamQuestionRetryOut,
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
    body.frontend_timestamp = to_ist(body.frontend_timestamp)
    backend_timestamp = to_ist(getattr(request.state, "received_at", None)) or istnow()
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
    body.frontend_timestamp = to_ist(body.frontend_timestamp)
    backend_timestamp = to_ist(getattr(request.state, "received_at", None)) or istnow()
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


@router.post("/hint/{question_id}", response_model=TeamQuestionHintOut, summary="View or purchase a question hint")
async def get_question_hint(
    question_id: uuid.UUID,
    body: TeamQuestionHintIn,
    request: Request,
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamQuestionHintOut:
    """
    View or purchase a hint for a question (Requires Team JWT):
    Step 1: Check frontend_timestamp against game clock and freeze state.
    Step 2: Validate question & path against team state (if null, logs START and locks team path/question).
    Step 3: Check if question is blocked.
    Step 4: Unified hint check / purchase:
       - If HINT12 requested and H1/H2 already purchased, reject (cannot buy two at once).
       - If requested hint is already owned (including via H12_PURCHASED), return hint(s) for 0 points.
       - Else calculate hint cost, verify team points, deduct, log purchase event, and return hint(s).
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
    body.frontend_timestamp = to_ist(body.frontend_timestamp)
    backend_timestamp = to_ist(getattr(request.state, "received_at", None)) or istnow()
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

    # Step 3: Check if question is blocked
    if (
        question.is_blocked is not None
        and body.frontend_timestamp < question.is_blocked
        and (question.unlocked_by_team_id is None or current_team.team_id not in question.unlocked_by_team_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question is blocked until {question.is_blocked.isoformat()}",
        )

    # Step 4: Hint purchase / view
    stmt = select(TeamLog.event_type).where(
        TeamLog.team_id == current_team.team_id,
        TeamLog.question_id == question_id,
        TeamLog.path_id == body.path_id,
        TeamLog.event_type.in_([
            QuestionEvent.H1_PURCHASED,
            QuestionEvent.H2_PURCHASED,
            QuestionEvent.H12_PURCHASED,
        ]),
    )
    purchased_events = set((await db.scalars(stmt)).all())

    # HINT12 mutual exclusion check
    if body.hint_type == HintType.HINT12 and (
        QuestionEvent.H1_PURCHASED in purchased_events or QuestionEvent.H2_PURCHASED in purchased_events
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One hint already purchased, cannot purchase two at once",
        )

    # Configuration for hint mapping
    hint_config = {
        HintType.HINT1: {
            "event": QuestionEvent.H1_PURCHASED,
            "store_key": "HINT1",
            "hints": {"hint1": question.hint1},
            "already_owned": (
                QuestionEvent.H1_PURCHASED in purchased_events
                or QuestionEvent.H12_PURCHASED in purchased_events
            ),
        },
        HintType.HINT2: {
            "event": QuestionEvent.H2_PURCHASED,
            "store_key": "HINT2",
            "hints": {"hint2": question.hint2},
            "already_owned": (
                QuestionEvent.H2_PURCHASED in purchased_events
                or QuestionEvent.H12_PURCHASED in purchased_events
            ),
        },
        HintType.HINT12: {
            "event": QuestionEvent.H12_PURCHASED,
            "store_key": "HINT12",
            "hints": {"hint1": question.hint1, "hint2": question.hint2},
            "already_owned": QuestionEvent.H12_PURCHASED in purchased_events,
        },
    }
    cfg = hint_config[body.hint_type]

    # If already owned, return without charging
    if cfg["already_owned"]:
        if is_unstarted:
            await db.execute(
                update(Team)
                .where(Team.team_id == current_team.team_id)
                .values(current_question_id=question_id, current_path_id=body.path_id)
            )
            await db.commit()
        return TeamQuestionHintOut(
            **cfg["hints"],
            points_deducted=Decimal("0.00"),
            current_points=current_team.points,
        )

    # Otherwise, calculate cost and purchase
    calc_points = calculate_question_points(
        question.is_viewed,
        game_state.start_at,
        body.frontend_timestamp,
        question.base_points,
    )
    points = Decimal(str(calc_points)) if calc_points is not None else question.base_points

    store_item = await db.get(StorePrice, cfg["store_key"])
    multiplier = store_item.value if (store_item and store_item.value is not None) else Decimal("0.00")

    calc_hint = calculate_hint_value(points, multiplier)
    hint_cost = Decimal(str(calc_hint)) if calc_hint is not None else (points * multiplier)

    if current_team.points < hint_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot buy hint: insufficient points",
        )

    new_points = current_team.points - hint_cost

    purchase_log = TeamLog(
        team_id=current_team.team_id,
        question_id=question_id,
        path_id=body.path_id,
        event_type=cfg["event"],
        created_at=body.frontend_timestamp,
        points=new_points,
    )
    db.add(purchase_log)

    team_updates: dict[str, Any] = {"points": new_points}
    if is_unstarted:
        team_updates["current_question_id"] = question_id
        team_updates["current_path_id"] = body.path_id

    await db.execute(
        update(Team)
        .where(Team.team_id == current_team.team_id)
        .values(**team_updates)
    )
    await db.commit()

    return TeamQuestionHintOut(
        **cfg["hints"],
        points_deducted=hint_cost,
        current_points=new_points,
    )


@router.post("/retry/{question_id}", response_model=TeamQuestionRetryOut, summary="Purchase a retry for a question")
async def purchase_question_retry(
    question_id: uuid.UUID,
    body: TeamQuestionRetryIn,
    request: Request,
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamQuestionRetryOut:
    """
    Purchase a retry for a question (Requires Team JWT):
    Step 1: Check frontend_timestamp against game clock and freeze state.
    Step 2: Validate question & path against team state:
       - If unstarted (current_question_id is None): return 400 "First exhaust question retries".
       - If active: verify question_id & path_id match current progress.
    Step 3: Check if question is blocked.
    Step 4: Verify that current retries are exhausted (wrong_count >= retries + retry_count).
    Step 5: Calculate retry cost, verify team points, deduct, log RETRY_PURCHASED, and update team.
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
    body.frontend_timestamp = to_ist(body.frontend_timestamp)
    backend_timestamp = to_ist(getattr(request.state, "received_at", None)) or istnow()
    validate_frontend_timestamp(
        frontend_timestamp=body.frontend_timestamp,
        backend_timestamp=backend_timestamp,
        start_at=game_state.start_at,
        end_at=game_state.end_at,
        paused_until=game_state.paused_until,
        frozen_until=current_team.frozen_until,
    )

    # Step 2: Validate question & path progression
    if current_team.current_question_id is None and current_team.current_path_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First exhaust question retries",
        )

    if current_team.current_question_id != question_id or current_team.current_path_id != body.path_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong question",
        )

    # Step 3: Check if question is blocked
    if (
        question.is_blocked is not None
        and body.frontend_timestamp < question.is_blocked
        and (question.unlocked_by_team_id is None or current_team.team_id not in question.unlocked_by_team_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question is blocked until {question.is_blocked.isoformat()}",
        )

    # Step 4: Verify current retries are exhausted
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

    if wrong_count < (question.retries + retry_count):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First exhaust question retries",
        )

    # Step 5: Calculate retry cost and purchase
    calc_points = calculate_question_points(
        question.is_viewed,
        game_state.start_at,
        body.frontend_timestamp,
        question.base_points,
    )
    points = Decimal(str(calc_points)) if calc_points is not None else question.base_points

    store_item = await db.get(StorePrice, "RETRY")
    multiplier = store_item.value if (store_item and store_item.value is not None) else Decimal("0.00")

    calc_retry = calculate_retry_value(points, multiplier)
    retry_cost = Decimal(str(calc_retry)) if calc_retry is not None else (points * multiplier)

    if current_team.points < retry_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot buy retry: insufficient points",
        )

    new_points = current_team.points - retry_cost

    retry_log = TeamLog(
        team_id=current_team.team_id,
        question_id=question_id,
        path_id=body.path_id,
        event_type=QuestionEvent.RETRY_PURCHASED,
        created_at=body.frontend_timestamp,
        points=new_points,
    )
    db.add(retry_log)

    await db.execute(
        update(Team)
        .where(Team.team_id == current_team.team_id)
        .values(points=new_points)
    )
    await db.commit()

    return TeamQuestionRetryOut(
        message="Retry purchased successfully",
        points_deducted=retry_cost,
        current_points=new_points,
        remaining_retries=1,
    )


@router.post("/block/{question_id}", response_model=TeamQuestionBlockOut, summary="Block a question")
async def block_question(
    question_id: uuid.UUID,
    body: TeamQuestionBlockIn,
    request: Request,
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamQuestionBlockOut:
    """
    Block a question (Requires Team JWT):
    Step 1: Check frontend_timestamp against game clock and freeze state.
    Step 2: Validate question & path progression:
       - If unstarted (current_question_id is None and current_path_id is None): return 400 "Cannot block unsolved question".
       - Else verify current_path_id matches body.path_id and question_id is in path_obj.questions.
    Step 3: Check that team is the first to solve this question.
    Step 4: Check points, calculate block time, set is_blocked in IST, deduct points, and log BLOCKED.
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
    body.frontend_timestamp = to_ist(body.frontend_timestamp)
    backend_timestamp = to_ist(getattr(request.state, "received_at", None)) or istnow()
    validate_frontend_timestamp(
        frontend_timestamp=body.frontend_timestamp,
        backend_timestamp=backend_timestamp,
        start_at=game_state.start_at,
        end_at=game_state.end_at,
        paused_until=game_state.paused_until,
        frozen_until=current_team.frozen_until,
    )

    # Step 2: Validate question & path progression
    if current_team.current_question_id is None and current_team.current_path_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block unsolved question",
        )

    if current_team.current_path_id != body.path_id or question_id not in path_obj.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong question",
        )

    # Step 3: Check that current team was first to solve
    if question.first_solved_by_team_id != current_team.team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You didn't solve it",
        )

    if question.is_blocked is not None and to_ist(question.is_blocked) > istnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question is already blocked until {to_ist(question.is_blocked).isoformat()}",
        )

    # Step 4: Validate points, calculate block duration, and apply
    calc_orig = calculate_question_points(
        question.is_viewed,
        game_state.start_at,
        question.first_solved_at,
        question.base_points,
    )
    orig_points = Decimal(str(calc_orig)) if calc_orig is not None else question.base_points

    if body.point > orig_points:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You didn't receive this much points",
        )

    store_item = await db.get(StorePrice, "BLOCK")
    multiplier = store_item.value if (store_item and store_item.value is not None) else Decimal("0.00")

    calc_block = calculate_block_time(body.point, multiplier)
    blocked_seconds = int(calc_block) if calc_block is not None else int(body.point * multiplier)

    blocked_until = istnow() + timedelta(seconds=blocked_seconds)
    question.is_blocked = blocked_until
    question.unlocked_by_team_id = [current_team.team_id]

    new_points = current_team.points - body.point

    block_log = TeamLog(
        team_id=current_team.team_id,
        question_id=question_id,
        path_id=body.path_id,
        event_type=QuestionEvent.BLOCKED,
        created_at=to_ist(body.frontend_timestamp),
        points=new_points,
    )
    db.add(block_log)

    await db.execute(
        update(Team)
        .where(Team.team_id == current_team.team_id)
        .values(points=new_points)
    )
    await db.commit()

    return TeamQuestionBlockOut(
        message="Question blocked successfully",
        is_blocked=blocked_until,
        points_deducted=body.point,
        current_points=new_points,
    )
