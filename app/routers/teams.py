from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.cookies import TEAM_COOKIE, clear_auth_cookie, set_auth_cookie
from app.deps import DB
from app.schemas.team import LeaderDetails, TeamLoginIn, TeamLoginOut, TeamProfileOut
from app.verify import (
    create_access_token,
    verify_access_token,
    verify_team_credentials,
    verify_team_payload,
)

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/teams", tags=["teams"])


def get_team_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract JWT token from HttpOnly cookie or Authorization Bearer header."""
    # 1. HttpOnly cookie (preferred, prevents JS/user inspection)
    token = request.cookies.get(TEAM_COOKIE) or request.cookies.get("access_token")
    if token:
        return token

    # 2. Authorization Bearer header (for Swagger UI / API tools)
    if credentials and credentials.credentials:
        return credentials.credentials

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ==========================================
# Team Route 1: Team Login (Public)
# ==========================================
@router.post("/login", response_model=TeamLoginOut, summary="Team Login")
async def team_login(body: TeamLoginIn, response: Response, db: DB) -> TeamLoginOut:
    """Authenticate team and store JWT in an HttpOnly cookie so the user cannot view it."""
    team = await verify_team_credentials(body.username, body.password, db)

    access_token = create_access_token({
        "team_id": str(team.team_id),
        "role": "team",
        "username": team.username,
        "team_name": team.team_name,
    })

    # Set as HttpOnly cookie (JavaScript / document.cookie cannot read this)
    set_auth_cookie(response, role="team", token=access_token)

    return TeamLoginOut(
        message="Login successful",
        team_id=team.team_id,
        role="team",
    )


# ==========================================
# Team Route 2: Get Team Profile (Requires Team JWT)
# ==========================================
@router.get("/profile", response_model=TeamProfileOut, summary="Get Team Profile")
async def get_team_profile(
    db: DB,
    token: str = Depends(get_team_token),
) -> TeamProfileOut:
    """Fetch current team profile: team name, members, and leader details."""
    payload = verify_access_token(token)
    team, team_id, username = await verify_team_payload(payload, db)

    return TeamProfileOut(
        team_id=team.team_id,
        team_name=team.team_name,
        team_members=team.team_members or [],
        leader_details=LeaderDetails(**team.leader_details),
    )


# ==========================================
# Team Route 3: Team Logout
# ==========================================
@router.post("/logout", summary="Team Logout")
async def team_logout(response: Response) -> dict[str, str]:
    """Clear the team HttpOnly authentication cookie."""
    clear_auth_cookie(response, role="team")
    return {"message": "Logged out successfully"}
