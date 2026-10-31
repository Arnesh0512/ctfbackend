import uuid
from datetime import time
from decimal import Decimal

from fastapi import APIRouter, status

from app.core.security import hash_password
from app.deps import DB
from app.models.team import Team
from app.schemas.admin import AdminLoginIn, AdminLoginOut
from app.schemas.team import CreateTeamIn, TeamOut
from app.verify import (
    create_access_token,
    verify_admin_credentials,
    verify_team_username,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ==========================================
# Admin Route 1: Admin Login
# ==========================================
@router.post("/login", response_model=AdminLoginOut, summary="Admin Login")
async def admin_login(body: AdminLoginIn, db: DB) -> AdminLoginOut:
    """Authenticate admin with admin_name and passcode, returning a signed JWT token."""
    admin = await verify_admin_credentials(body.admin_name, body.passcode, db)

    access_token = create_access_token({
        "admin_id": str(admin.admin_id),
        "role": "admin",
        "admin_name": admin.admin_name,
    })

    return AdminLoginOut(
        access_token=access_token,
        token_type="bearer",
        admin_id=admin.admin_id,
        role="admin",
    )


# ==========================================
# Admin Route 2: Create Team
# ==========================================
@router.post(
    "/teams",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
)
async def create_team(body: CreateTeamIn, db: DB) -> TeamOut:
    """Create a new team with autofilled default state fields."""
    await verify_team_username(body.username, db)

    new_team = Team(
        team_id=uuid.uuid4(),
        team_name=body.team_name,
        team_members=body.team_members,
        leader_details=body.leader_details.model_dump(),
        username=body.username,
        password=hash_password(body.password),
        points=Decimal("0.00"),
        powerups_used=0,
        playthrough=time(0, 0, 0),
        has_reached_delhi=False,
        current_path_id=None,
        current_question_id=None,
        frozen_until=None,
        developer_time=time(0, 0, 0),
        skip=None,
    )

    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)

    return TeamOut.model_validate(new_team)
