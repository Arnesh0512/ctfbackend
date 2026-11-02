from typing import Annotated, Any

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import ADMIN_COOKIE, TEAM_COOKIE
from app.core.db import get_db
from app.core.supabase_auth import fetch_admin_from_postgrest, fetch_team_from_postgrest
from app.schemas.team import TeamOut

DB = Annotated[AsyncSession, Depends(get_db)]
_security = HTTPBearer(auto_error=False)


def _get_token_from_request(
    request: Request,
    cookie_alias: str,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    token = request.cookies.get(cookie_alias) or request.cookies.get("access_token")
    if token:
        return token
    return None


async def get_current_team_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> str:
    token = _get_token_from_request(request, TEAM_COOKIE, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


async def get_current_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> str:
    token = _get_token_from_request(request, ADMIN_COOKIE, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


async def current_team(token: str = Depends(get_current_team_token)) -> TeamOut:
    team_data = await fetch_team_from_postgrest(token)
    if not team_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unauthorized team session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TeamOut.model_validate(team_data)


async def current_admin(token: str = Depends(get_current_admin_token)) -> dict[str, Any]:
    admin_data = await fetch_admin_from_postgrest(token)
    if not admin_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privilege required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin_data


CurrentTeam = Annotated[TeamOut, Depends(current_team)]
CurrentAdmin = Annotated[dict[str, Any], Depends(current_admin)]
