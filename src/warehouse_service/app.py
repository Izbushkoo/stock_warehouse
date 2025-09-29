"""FastAPI application factory for the unified warehouse service."""

from __future__ import annotations

from fastapi import FastAPI

from warehouse_service import __version__
from warehouse_service.config import get_settings
from warehouse_service.logging import configure_logging
from warehouse_service.routes import admin_router, api_router, catalog_router, web_router, permissions_web_router, warehouses_router
from warehouse_service.routes.user_management import router as user_management_router
from warehouse_service.middleware.auth import AuthMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add authentication and authorization middleware
    app.add_middleware(AuthMiddleware)

    app.include_router(api_router)
    app.include_router(admin_router)
    app.include_router(catalog_router)
    app.include_router(warehouses_router)
    app.include_router(permissions_web_router)
    app.include_router(user_management_router)
    app.include_router(web_router)

    @app.get("/health", tags=["monitoring"], summary="Return service health status")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
