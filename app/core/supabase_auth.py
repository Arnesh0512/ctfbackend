import secrets
import string
import uuid
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status

from app.core.config import settings


def generate_random_password(length: int = 10) -> str:
    """Generate a cryptographically random alphanumeric password of given length."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def to_auth_email(username: str) -> str:
    """Deterministically map a team username to a Supabase auth email."""
    cleaned = username.strip().lower()
    return f"{cleaned}@mayasabha.local"


def _extract_subject_from_jwt(token: str) -> uuid.UUID | None:
    """Extract subject (user_id) from JWT token without requiring the secret key."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        sub = payload.get("sub")
        return uuid.UUID(str(sub)) if sub else None
    except Exception:
        return None


async def create_team_auth_user(username: str, password: str) -> uuid.UUID:
    """Create a new team user in Supabase Auth via Admin API and return the generated user_id."""
    url = f"{settings.supabase_url}/auth/v1/admin/users"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": to_auth_email(username),
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "username": username,
            "role": "team",
        },
        "app_metadata": {
            "role": "team",
        },
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != status.HTTP_200_OK:
            error_msg = response.text
            try:
                error_msg = response.json().get("msg", error_msg)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create team in Supabase Auth: {error_msg}",
            )
        data = response.json()
        user_id = data.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase Auth did not return a user identifier",
            )
        return uuid.UUID(str(user_id))


async def update_team_auth_password(team_id: uuid.UUID, new_password: str) -> None:
    """Update a team user's password in Supabase Auth via Admin API."""
    url = f"{settings.supabase_url}/auth/v1/admin/users/{team_id}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "password": new_password,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.put(url, headers=headers, json=payload)
        if response.status_code != status.HTTP_200_OK:
            error_msg = response.text
            try:
                error_msg = response.json().get("msg", error_msg)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update password in Supabase Auth: {error_msg}",
            )


async def delete_team_auth_user(team_id: uuid.UUID) -> None:
    """Delete a team user from Supabase Auth via Admin API (used for rollback)."""
    url = f"{settings.supabase_url}/auth/v1/admin/users/{team_id}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.delete(url, headers=headers)


async def login_with_supabase(email: str, password: str) -> dict[str, Any]:
    """Authenticate with Supabase GoTrue password grant and return token session."""
    url = f"{settings.supabase_url}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json",
    }
    payload = {
        "email": email.strip(),
        "password": password,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials",
            )
        return response.json()


async def fetch_team_from_postgrest(jwt_token: str) -> dict[str, Any] | None:
    """
    Validate the team JWT against Supabase PostgREST and return the team record.
    Returns None if JWT is invalid, expired, or does not correspond to a team in public.teams.
    """
    user_id = _extract_subject_from_jwt(jwt_token)
    if not user_id:
        return None

    url = f"{settings.supabase_url}/rest/v1/teams?team_id=eq.{user_id}&select=*"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.pgrst.object+json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == status.HTTP_200_OK:
                return response.json()
            return None
    except Exception:
        return None


async def fetch_admin_from_postgrest(jwt_token: str) -> dict[str, Any] | None:
    """
    Validate the admin JWT against Supabase PostgREST and return the admin record.
    Returns None if JWT is invalid, expired, or does not correspond to an admin in public.admins.
    """
    user_id = _extract_subject_from_jwt(jwt_token)
    if not user_id:
        return None

    url = f"{settings.supabase_url}/rest/v1/admins?admin_id=eq.{user_id}&select=*"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.pgrst.object+json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == status.HTTP_200_OK:
                return response.json()
            return None
    except Exception:
        return None
