from fastapi import APIRouter

from app.deps import DB
from app.schemas.team import TeamLoginIn, TeamLoginOut
from app.verify import create_access_token, verify_team_credentials

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
