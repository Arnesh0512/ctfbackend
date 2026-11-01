from fastapi import APIRouter

from app.routers.admin.auth import router as auth_router
from app.routers.admin.file import router as file_router
from app.routers.admin.game import router as game_router
from app.routers.admin.path import router as path_router
from app.routers.admin.question import router as question_router
from app.routers.admin.store import router as store_router
from app.routers.admin.team import router as team_router
from app.routers.admin.time import router as time_router

router = APIRouter(prefix="/admin")

router.include_router(auth_router)
router.include_router(team_router)
router.include_router(game_router)
router.include_router(time_router)
router.include_router(store_router)
router.include_router(file_router)
router.include_router(question_router)
router.include_router(path_router)
