from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.supabase_auth import (
    create_team_auth_user,
    delete_team_auth_user,
    generate_random_password,
    update_team_auth_password,
)
from app.deps import DB
from app.models.team import Team
from app.routers.admin.deps import _assert_before_game_start, verify_admin
from app.schemas.admin import AdminTeamItemOut, AdminTeamUpdateIn
from app.schemas.team import CreateTeamIn, TeamCredentialsIn, TeamCredentialsOut, TeamOut
from app.verify.team import verify_team_username

router = APIRouter(prefix="/teams", tags=["admin: /teams"], dependencies=[Depends(verify_admin)])


@router.post(
    "",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
)
async def create_team(
    body: CreateTeamIn,
    db: DB,
) -> TeamOut:
    """Create a new team before the game starts (Requires Admin JWT). Generates a random 10-char password in Supabase Auth."""
    await _assert_before_game_start(db, action="create")
    await verify_team_username(body.username, db)

    # 1. Generate 10-character random password
    generated_password = generate_random_password(10)

    # 2. Create team user in Supabase Auth -> returns Supabase user_id
    supabase_user_id = await create_team_auth_user(body.username, generated_password)

    new_team = Team(
        team_id=supabase_user_id,
        team_name=body.team_name,
        team_members=body.team_members,
        leader_details=body.leader_details.model_dump(),
        username=body.username,
        password=generated_password,
        otp_valid=True,
        points=Decimal("0.00"),
        powerups_used=0,
        has_reached_delhi=None,
        current_path_id=None,
        current_question_id=None,
        frozen_until=None,
        developer_time=False,
        skip=None,
    )

    try:
        db.add(new_team)
        await db.commit()
        await db.refresh(new_team)
    except Exception:
        # Rollback user in Supabase Auth if DB commit fails
        await delete_team_auth_user(supabase_user_id)
        raise

    return TeamOut.model_validate(new_team)


@router.post(
    "/credentials",
    response_model=TeamCredentialsOut,
    summary="Get or re-issue team credentials",
)
async def get_or_reissue_team_credentials(
    body: TeamCredentialsIn,
    db: DB,
) -> TeamCredentialsOut:
    """
    Get or re-issue credentials for a team.
    - If otp_valid is True: returns current credentials without modifying them.
    - If otp_valid is False: generates a new 10-char password, updates Supabase Auth and DB, sets otp_valid=True, and returns credentials.
    """
    team = await db.get(Team, body.team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID '{body.team_id}' not found.",
        )

    if team.otp_valid:
        return TeamCredentialsOut(
            team_id=team.team_id,
            team_name=team.team_name,
            username=team.username,
            password=team.password,
            otp_valid=True,
        )

    # otp_valid is False -> generate new 10-character password and update Supabase & DB
    new_password = generate_random_password(10)
    await update_team_auth_password(team.team_id, new_password)

    team.password = new_password
    team.otp_valid = True
    await db.commit()
    await db.refresh(team)

    return TeamCredentialsOut(
        team_id=team.team_id,
        team_name=team.team_name,
        username=team.username,
        password=team.password,
        otp_valid=True,
    )


@router.get(
    "",
    response_model=list[AdminTeamItemOut],
    summary="Fetch all teams",
)
async def get_all_teams(
    db: DB,
) -> list[AdminTeamItemOut]:
    """Fetch all teams with team_name, username, password, and leader_name."""
    stmt = select(Team).order_by(Team.team_name.asc())
    teams = (await db.scalars(stmt)).all()

    return [
        AdminTeamItemOut(
            team_id=team.team_id,
            team_name=team.team_name,
            username=team.username,
            password=team.password,
            leader_name=team.leader_details.get("name", "") if team.leader_details else "",
            leader_enrollment=team.leader_details.get("enrollment", "") if team.leader_details else "",
        )
        for team in teams
    ]


@router.get(
    "/{team_id}",
    response_model=TeamOut,
    summary="Get team by ID",
)
async def get_team_by_id(
    team_id: uuid.UUID,
    db: DB,
) -> TeamOut:
    """Fetch details of a single team by team_id (Requires Admin JWT)."""
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID '{team_id}' not found.",
        )

    return TeamOut.model_validate(team)


@router.patch(
    "/{team_id}",
    response_model=TeamOut,
    summary="Update team by ID",
)
async def update_team_by_id(
    team_id: uuid.UUID,
    body: AdminTeamUpdateIn,
    db: DB,
) -> TeamOut:
    """Update team details before the game starts (Requires Admin JWT)."""
    await _assert_before_game_start(db, action="modify")

    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID '{team_id}' not found.",
        )

    if body.username is not None and body.username.strip() != team.username:
        await verify_team_username(body.username, db)
        team.username = body.username.strip()

    if body.team_name is not None:
        team.team_name = body.team_name.strip()

    if body.password is not None:
        await update_team_auth_password(team.team_id, body.password)
        team.password = body.password

    if body.team_members is not None:
        team.team_members = body.team_members

    if body.leader_details is not None:
        team.leader_details = body.leader_details.model_dump()

    await db.commit()
    await db.refresh(team)

    return TeamOut.model_validate(team)
