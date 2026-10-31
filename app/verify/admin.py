import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.admin import Admin


async def verify_admin_credentials(
    admin_name: str,
    passcode: str,
    db: AsyncSession,
) -> Admin:
    """Verify admin login credentials against the database."""
    admin_name = admin_name.strip()
    admin = await db.scalar(select(Admin).where(Admin.admin_name == admin_name))
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    matches = (admin.passcode == passcode) or verify_password(passcode, admin.passcode)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    return admin


async def verify_admin_payload(
    payload: dict[str, Any],
    db: AsyncSession,
) -> tuple[Admin, uuid.UUID, str]:
    """Verify that decoded token payload represents a valid active admin in database."""
    admin_id_raw = payload.get("admin_id")
    role = payload.get("role")

    if not admin_id_raw or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privilege required",
        )

    try:
        admin_id = uuid.UUID(str(admin_id_raw))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin identifier in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = await db.scalar(select(Admin).where(Admin.admin_id == admin_id))
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    return admin, admin.admin_id, admin.admin_name
