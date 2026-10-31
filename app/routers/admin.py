import uuid
from datetime import time
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import hash_password
from app.deps import DB
from app.models.team import Team
from app.schemas.admin import AdminLoginIn, AdminLoginOut, AdminProfileOut
from app.schemas.team import CreateTeamIn, TeamOut
from app.verify import (
    create_access_token,
    verify_access_token,
    verify_admin_credentials,
    verify_admin_payload,
    verify_team_username,
)

security = HTTPBearer()

router = APIRouter(prefix="/admin", tags=["admin"])
admins_router = APIRouter(prefix="/admins", tags=["admins"])


# ==========================================
# Admin Route 1: Admin Login
# ==========================================
@router.post("/login", response_model=AdminLoginOut, summary="Admin Login")
@admins_router.post("/login", response_model=AdminLoginOut, summary="Admin Login (/admins alias)")
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
# Admin Route 2: Get Admin Profile
# ==========================================
@router.get("/profile", response_model=AdminProfileOut, summary="Get current admin profile")
@admins_router.get("/profile", response_model=AdminProfileOut, summary="Get current admin profile (/admins alias)")
async def get_admin_profile(
    db: DB,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AdminProfileOut:
    """Fetch current authenticated admin details from JWT token."""
    payload = verify_access_token(credentials.credentials)
    admin, admin_id, admin_name = await verify_admin_payload(payload, db)

    return AdminProfileOut(
        admin_id=admin.admin_id,
        admin_name=admin.admin_name,
        role="admin",
    )


# ==========================================
# Admin Route 3: Create Team
# ==========================================
@router.post(
    "/teams",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
)
@router.post(
    "/create-team",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@admins_router.post(
    "/teams",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team (/admins alias)",
)
@admins_router.post(
    "/create-team",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_team(body: CreateTeamIn, db: DB) -> TeamOut:
    """Create a new team with autofilled default state fields."""
    await verify_team_username(body.username, db, type="N")

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
