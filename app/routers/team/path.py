from datetime import timedelta
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update

from app.core.clock import istnow, to_ist
from app.core.time import validate_frontend_timestamp
from app.deps import DB
from app.models.content import Path, Question
from app.models.enums import QuestionEvent
from app.models.game import GameState, StorePrice
from app.models.logs import TeamLog
from app.models.team import Team
from app.routers.team.auth import get_current_team
from app.schemas.path import (
    TeamCurrentPathOut,
    TeamPathChangeIn,
    TeamPathChangeOut,
    TeamPathOut,
    TeamPathQuestionItem,
)
from app.schemas.team import TeamOut

router = APIRouter(prefix="/path", tags=["teams: /path"])


@router.get("", response_model=list[TeamPathOut], summary="Get all paths (Public, No JWT)")
async def get_team_paths(db: DB) -> list[TeamPathOut]:
    """
    Fetch all paths and return a list of dictionaries containing path_id
    and question_list with question_id, state, and monument. No JWT authentication required.
    """
    paths = (await db.scalars(select(Path).order_by(Path.path_name.asc()))).all()
    all_qids = {qid for p in paths if p.questions for qid in p.questions}

    if all_qids:
        questions = (
            await db.scalars(select(Question).where(Question.question_id.in_(all_qids)))
        ).all()
        q_map = {q.question_id: q for q in questions}
    else:
        q_map = {}

    return [
        TeamPathOut(
            path_id=p.path_id,
            question_list=[
                TeamPathQuestionItem(
                    question_id=qid,
                    state=q_map[qid].state,
                    monument=q_map[qid].monument,
                )
                for qid in (p.questions or [])
                if qid in q_map
            ],
        )
        for p in paths
    ]


@router.get("/current", response_model=TeamCurrentPathOut, summary="Get current path for team")
async def get_current_team_path(
    current_team: TeamOut = Depends(get_current_team),
) -> TeamCurrentPathOut:
    """Fetch the current_path_id for the authenticated team (Requires Team JWT)."""
    return TeamCurrentPathOut(current_path_id=current_team.current_path_id)


@router.post("/change/{path_id}", response_model=TeamPathChangeOut, summary="Change current path for team")
async def change_team_path(
    path_id: uuid.UUID,
    body: TeamPathChangeIn,
    request: Request,
    current_team: TeamOut = Depends(get_current_team),
    db: DB = None,
) -> TeamPathChangeOut:
    """
    Change team's active path (Requires Team JWT):
    - Validates frontend timestamp against game state and freeze state.
    - Ensures team has an active path/question and matches path_id and body.question_id.
    - Prevents changing to the same path.
    - Resolves resume question on new path:
      - If team previously entered and left new path:
        - If previous event was END or solved/blocked on the last question: 400 (already completed).
        - If ANSWER_CORRECT, SKIPPED, or BLOCKED: advances to next question.
        - If VIEW, ANSWER_WRONG, RETRY_PURCHASED, UNBLOCKED, H1/H2/H12_PURCHASED, START: resumes at that question.
      - Else: starts at the first question of new path.
    - type == 'COST': deducts PATHCHANGEC store points, logs LEFT, NO_WAIT, START at frontend_timestamp.
    - type == 'TIME': freezes team for PATHCHANGET store seconds, logs LEFT, WAIT at frontend_timestamp, START at frozen_until.
    - Updates team's current_path_id, current_question_id, points, and frozen_until.
    """
    game_state = await db.scalar(select(GameState))
    if not game_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game state not found.")

    old_path = await db.get(Path, path_id)
    if not old_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found.")

    new_path = await db.get(Path, body.new_path_id)
    if not new_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New path not found.")

    if not new_path.questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New path has no questions.")

    # Step 1: Check timestamp
    body.frontend_timestamp = to_ist(body.frontend_timestamp)
    backend_timestamp = to_ist(getattr(request.state, "received_at", None)) or istnow()
    validate_frontend_timestamp(
        frontend_timestamp=body.frontend_timestamp,
        backend_timestamp=backend_timestamp,
        start_at=game_state.start_at,
        end_at=game_state.end_at,
        pause_start_at=game_state.pause_start_at,
        pause_end_at=game_state.pause_end_at,
        frozen_until=current_team.frozen_until,
    )

    # Step 2: If current_path_id is null and current_question_id is null
    if current_team.current_path_id is None or current_team.current_question_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change path until you start one",
        )

    # Step 3: Check if currently on this path and question
    if current_team.current_path_id != path_id or current_team.current_question_id != body.question_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Currently not on this path or question",
        )

    if body.new_path_id == path_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change to the same path",
        )

    # Step 4: Resolve target question on new_path_id
    stmt_latest_left = (
        select(TeamLog)
        .where(
            TeamLog.team_id == current_team.team_id,
            TeamLog.path_id == body.new_path_id,
            TeamLog.event_type == QuestionEvent.LEFT,
        )
        .order_by(TeamLog.created_at.desc())
    )
    latest_left = await db.scalar(stmt_latest_left)

    if latest_left is not None:
        stmt_prev_event = (
            select(TeamLog)
            .where(
                TeamLog.team_id == current_team.team_id,
                TeamLog.path_id == body.new_path_id,
                TeamLog.created_at <= latest_left.created_at,
                TeamLog.event_type.not_in([QuestionEvent.LEFT, QuestionEvent.WAIT, QuestionEvent.NO_WAIT]),
            )
            .order_by(TeamLog.created_at.desc())
        )
        prev_log = await db.scalar(stmt_prev_event)

        if prev_log is not None:
            if prev_log.event_type == QuestionEvent.END:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change to an already completed path",
                )
            if prev_log.event_type in [
                QuestionEvent.ANSWER_CORRECT,
                QuestionEvent.SKIPPED,
                QuestionEvent.BLOCKED,
            ]:
                if prev_log.question_id not in new_path.questions:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Previous question not found in new path questions",
                    )
                idx = new_path.questions.index(prev_log.question_id)
                if idx >= len(new_path.questions) - 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot change to an already completed path",
                    )
                current_ques_id = new_path.questions[idx + 1]
            elif prev_log.event_type in [
                QuestionEvent.VIEW,
                QuestionEvent.ANSWER_WRONG,
                QuestionEvent.RETRY_PURCHASED,
                QuestionEvent.UNBLOCKED,
                QuestionEvent.H1_PURCHASED,
                QuestionEvent.H2_PURCHASED,
                QuestionEvent.H12_PURCHASED,
                QuestionEvent.START,
            ]:
                current_ques_id = prev_log.question_id
            else:
                current_ques_id = new_path.questions[0]
        else:
            current_ques_id = new_path.questions[0]
    else:
        current_ques_id = new_path.questions[0]

    # Step 5: Process type (COST or TIME)
    old_path_id = path_id
    if body.type == "COST":
        store_item = await db.get(StorePrice, "PATHCHANGEC")
        cost = store_item.value if (store_item and store_item.value is not None) else Decimal("0.00")
        if current_team.points < cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change path: insufficient points",
            )
        new_points = current_team.points - cost
        new_frozen_until = current_team.frozen_until

        left_log = TeamLog(
            team_id=current_team.team_id,
            question_id=body.question_id,
            path_id=old_path_id,
            event_type=QuestionEvent.LEFT,
            created_at=to_ist(body.frontend_timestamp),
            points=new_points,
        )
        wait_log = TeamLog(
            team_id=current_team.team_id,
            question_id=current_ques_id,
            path_id=body.new_path_id,
            event_type=QuestionEvent.NO_WAIT,
            created_at=to_ist(body.frontend_timestamp),
            points=new_points,
        )
        start_log = TeamLog(
            team_id=current_team.team_id,
            question_id=current_ques_id,
            path_id=body.new_path_id,
            event_type=QuestionEvent.START,
            created_at=to_ist(body.frontend_timestamp),
            points=new_points,
        )
        db.add_all([left_log, wait_log, start_log])
        message = "Path change successful"

    elif body.type == "TIME":
        store_item = await db.get(StorePrice, "PATHCHANGET")
        time_seconds = float(store_item.value if (store_item and store_item.value is not None) else Decimal("0.00"))
        new_points = current_team.points
        new_frozen_until = to_ist(body.frontend_timestamp + timedelta(seconds=time_seconds))

        left_log = TeamLog(
            team_id=current_team.team_id,
            question_id=body.question_id,
            path_id=old_path_id,
            event_type=QuestionEvent.LEFT,
            created_at=to_ist(body.frontend_timestamp),
            points=new_points,
        )
        wait_log = TeamLog(
            team_id=current_team.team_id,
            question_id=current_ques_id,
            path_id=body.new_path_id,
            event_type=QuestionEvent.WAIT,
            created_at=to_ist(body.frontend_timestamp),
            points=new_points,
        )
        start_log = TeamLog(
            team_id=current_team.team_id,
            question_id=current_ques_id,
            path_id=body.new_path_id,
            event_type=QuestionEvent.START,
            created_at=new_frozen_until,
            points=new_points,
        )
        db.add_all([left_log, wait_log, start_log])
        message = f"Path change successful, wait for {int(time_seconds)} seconds"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path change type",
        )

    # Step 6: Update team state in DB
    await db.execute(
        update(Team)
        .where(Team.team_id == current_team.team_id)
        .values(
            current_path_id=body.new_path_id,
            current_question_id=current_ques_id,
            points=new_points,
            frozen_until=new_frozen_until,
        )
    )
    await db.commit()

    return TeamPathChangeOut(
        message=message,
        current_path_id=body.new_path_id,
        current_question_id=current_ques_id,
        points=new_points,
        frozen_until=new_frozen_until,
    )
