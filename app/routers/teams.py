from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.deps import DB
from app.schemas.team import LeaderDetails, TeamLoginIn, TeamLoginOut, TeamProfileOut
from app.verify import (
    create_access_token,
    verify_access_token,
    verify_team_credentials,
    verify_team_payload,
)

security = HTTPBearer()

router = APIRouter(prefix="/teams", tags=["teams"])


# ==========================================
# Team Route 1: Team Login (Public)
# ==========================================
@router.post("/login", response_model=TeamLoginOut, summary="Team Login")
async def team_login(body: TeamLoginIn, db: DB) -> TeamLoginOut:
    """Authenticate a team using username and password, returning a signed JWT access token."""
    team = await verify_team_credentials(body.username, body.password, db)

    access_token = create_access_token({
        "team_id": str(team.team_id),
        "role": "team",
        "username": team.username,
        "team_name": team.team_name,
    })

    return TeamLoginOut(
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
    db: DB,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TeamProfileOut:
    """Fetch current team profile: team name, members, and leader details (Requires Team JWT)."""
    token = credentials.credentials
    payload = verify_access_token(token)
    team, team_id, username = await verify_team_payload(payload, db)

    return TeamProfileOut(
        team_id=team.team_id,
        team_name=team.team_name,
        team_members=team.team_members or [],
        leader_details=LeaderDetails(**team.leader_details),
    )
