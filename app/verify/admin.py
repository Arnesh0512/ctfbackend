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
