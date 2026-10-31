from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import admin_router, events_router


def create_app() -> FastAPI:
    prefix = settings.api_prefix
    docs = settings.docs_enabled
    app = FastAPI(
        title="MAYASABHA CTF BACKEND",
        docs_url=f"{prefix}/docs" if docs else None,
        redoc_url=None,
        openapi_url=f"{prefix}/openapi.json" if docs else None,
    )

    if settings.frontend_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.frontend_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["*"],
        )

    @app.get(f"{prefix}/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "mayasabha-ctf-backend"}

    # Include Admin and Events routers
    app.include_router(admin_router, prefix=prefix)
    app.include_router(events_router, prefix=prefix)

    return app


app = create_app()
