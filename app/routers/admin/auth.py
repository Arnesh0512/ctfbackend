from fastapi import APIRouter, Response

from app.core.cookies import set_auth_cookie
from app.deps import DB
from app.routers.admin.deps import get_admin_token, verify_admin
from app.schemas.admin import AdminLoginIn, AdminLoginOut
from app.verify.admin import verify_admin_credentials
from app.verify.token import create_access_token

router = APIRouter(tags=["admin: /"])


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
