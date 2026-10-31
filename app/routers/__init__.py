from app.routers.admin import admins_router, router as admin_router
from app.routers.events import router as events_router

__all__ = ["admin_router", "admins_router", "events_router"]
