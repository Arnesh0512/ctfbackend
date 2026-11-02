import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.cookies import set_auth_cookie
from app.core.supabase_auth import login_with_supabase
from app.deps import DB
from app.models.admin import Admin
from app.schemas.admin import AdminLoginIn, AdminLoginOut

router = APIRouter(tags=["admin: /"])


@router.post("/login", response_model=AdminLoginOut, summary="Admin Login")
async def admin_login(body: AdminLoginIn, response: Response, db: DB) -> AdminLoginOut:
    """Authenticate admin with admin_email and passcode via Supabase, returning Supabase JWT and setting HttpOnly cookie."""
    # 1. Authenticate with Supabase GoTrue
    auth_data = await login_with_supabase(body.admin_email, body.passcode)
    access_token = auth_data["access_token"]
    user_info = auth_data.get("user", {})
    user_id_raw = user_info.get("id")

    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    admin_id = uuid.UUID(str(user_id_raw))

    # 2. Verify that this user actually exists in public.admins
    admin = await db.scalar(select(Admin).where(Admin.admin_id == admin_id))
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Not an authorized admin",
        )

    # 3. Set HttpOnly cookie
    set_auth_cookie(response, role="admin", token=access_token)

    return AdminLoginOut(
        access_token=access_token,
        token_type="bearer",
        admin_id=admin.admin_id,
        role="admin",
    )
