from fastapi import APIRouter

from app.routers.team.auth import router as auth_router

router = APIRouter(prefix="/teams")
router.include_router(auth_router)
