from app.routers.admin import router as admin_router
from app.routers.events import router as events_router
from app.routers.teams import router as teams_router

__all__ = ["admin_router", "events_router", "teams_router"]
