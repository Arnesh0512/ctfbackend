import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.core.clock import utcnow
from app.core.events import broadcaster
from app.core.time import validate_frontend_timestamp
from app.deps import DB
from app.models.content import Path, Question
from app.models.enums import QuestionEvent
from app.models.game import GameState
from app.models.logs import TeamLog
from app.routers.team.auth import get_current_team
from app.schemas.question import TeamCurrentQuestionOut, TeamQuestionViewIn, TeamQuestionViewOut
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
