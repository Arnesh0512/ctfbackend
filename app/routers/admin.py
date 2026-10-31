import uuid
from datetime import time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.cookies import ADMIN_COOKIE, clear_auth_cookie, set_auth_cookie
from app.core.security import hash_password
from app.deps import DB
from app.models.team import Team
from app.schemas.admin import AdminLoginIn, AdminLoginOut, AdminTeamItemOut
from app.schemas.team import CreateTeamIn, TeamOut
from app.verify import (
    create_access_token,
    verify_access_token,
    verify_admin_credentials,
    verify_admin_payload,
    verify_team_username,
)

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract admin JWT token from HttpOnly cookie or Authorization Bearer header."""
    token = request.cookies.get(ADMIN_COOKIE) or request.cookies.get("access_token")
    if token:
        return token
    if credentials and credentials.credentials:
        return credentials.credentials
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ==========================================
# Admin Route 1: Admin Login (Public)
# ==========================================
@router.post("/login", response_model=AdminLoginOut, summary="Admin Login")
async def admin_login(body: AdminLoginIn, response: Response, db: DB) -> AdminLoginOut:
    """Authenticate admin with admin_name and passcode, returning a signed JWT token and HttpOnly cookie."""
    admin = await verify_admin_credentials(body.admin_name, body.passcode, db)

    access_token = create_access_token({
        "admin_id": str(admin.admin_id),
        "role": "admin",
        "admin_name": admin.admin_name,
    })

    # Set as HttpOnly cookie so the browser stores it securely
    set_auth_cookie(response, role="admin", token=access_token)

    return AdminLoginOut(
        access_token=access_token,
        token_type="bearer",
        admin_id=admin.admin_id,
        role="admin",
    )


# ==========================================
# Admin Route 2: Create Team (Requires Admin JWT)
# ==========================================
@router.post(
    "/teams",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
)
async def create_team(
    body: CreateTeamIn,
    db: DB,
    token: str = Depends(get_admin_token),
) -> TeamOut:
    """Create a new team with autofilled default state fields."""
    payload = verify_access_token(token)
    await verify_admin_payload(payload, db)

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


# ==========================================
# Admin Route 3: Fetch All Teams (Requires Admin JWT)
# ==========================================
@router.get(
    "/teams",
    response_model=list[AdminTeamItemOut],
    summary="Fetch all teams",
)
async def get_all_teams(
    db: DB,
    token: str = Depends(get_admin_token),
) -> list[AdminTeamItemOut]:
    """Fetch all teams with team_name, username, password, and leader_name."""
    payload = verify_access_token(token)
    await verify_admin_payload(payload, db)

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


# ==========================================
# Admin Route 4: Admin Logout
# ==========================================
@router.post("/logout", summary="Admin Logout")
async def admin_logout(response: Response) -> dict[str, str]:
    """Clear admin authentication HttpOnly cookie."""
    clear_auth_cookie(response, role="admin")
    return {"message": "Admin logged out successfully"}
