from fastapi import APIRouter

from app.routers.team.auth import router as auth_router
from app.routers.team.path import router as path_router
from app.routers.team.question import router as question_router
from app.routers.team.store import router as store_router

router = APIRouter(prefix="/teams")
router.include_router(auth_router)
router.include_router(store_router)
router.include_router(path_router)
router.include_router(question_router)
