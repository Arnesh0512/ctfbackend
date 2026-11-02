from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.cookies import TEAM_COOKIE, set_auth_cookie
from app.core.supabase_auth import fetch_team_from_postgrest, login_with_supabase, to_auth_email
from app.deps import DB
from app.models.team import Team
from app.schemas.team import LeaderDetails, TeamLoginIn, TeamLoginOut, TeamOut, TeamProfileOut

security = HTTPBearer(auto_error=False)

router = APIRouter(tags=["teams: /"])


def get_team_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract JWT token from Authorization Bearer header or HttpOnly cookie."""
    if credentials and credentials.credentials:
        return credentials.credentials
    token = request.cookies.get(TEAM_COOKIE) or request.cookies.get("access_token")
    if token:
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_team(token: str = Depends(get_team_token)) -> TeamOut:
    """Option 1: Supabase PostgREST validates JWT and returns the team record directly."""
    team_data = await fetch_team_from_postgrest(token)
    if not team_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unauthorized team session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TeamOut.model_validate(team_data)


# ==========================================
# Team Route 1: Team Login (Public)
# ==========================================
@router.post("/login", response_model=TeamLoginOut, summary="Team Login")
async def team_login(body: TeamLoginIn, response: Response, db: DB) -> TeamLoginOut:
    """
    Authenticate team:
    1. Checks if username exists and otp_valid is True.
    2. If otp_valid is False, returns HTTP 401 'Password expired'.
    3. Validates password via Supabase Auth and receives JWT.
    4. Sets otp_valid to False in database.
    5. Stores Supabase JWT in HttpOnly cookie and returns response.
    """
    username = body.username.strip()
    team = await db.scalar(select(Team).where(Team.username == username))
    if not team:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid team credentials",
        )

    if not team.otp_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password expired",
        )

    # Authenticate via Supabase Auth
    auth_email = to_auth_email(team.username)
    auth_data = await login_with_supabase(auth_email, body.password)
    access_token = auth_data["access_token"]

    # Invalidate OTP on successful login
    team.otp_valid = False
    await db.commit()

    # Set as HttpOnly cookie (JavaScript / document.cookie cannot read this)
    set_auth_cookie(response, role="team", token=access_token)

    return TeamLoginOut(
        message="Login successful",
        access_token=access_token,
        token_type="bearer",
        team_id=team.team_id,
        role="team",
    )


# ==========================================
# Team Route 2: Get Team Profile (Requires Team JWT)
# ==========================================
@router.get("/profile", response_model=TeamProfileOut, summary="Get Team Profile")
async def get_team_profile(
    current_team: TeamOut = Depends(get_current_team),
) -> TeamProfileOut:
    """Fetch current team profile: team name, members, and leader details automatically from Supabase."""
    return TeamProfileOut(
        team_id=current_team.team_id,
        team_name=current_team.team_name,
        team_members=current_team.team_members or [],
        leader_details=current_team.leader_details,
    )
