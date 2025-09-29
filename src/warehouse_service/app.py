"""FastAPI application factory for the unified warehouse service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from warehouse_service import __version__
from warehouse_service.config import get_settings
from warehouse_service.logging import configure_logging
from warehouse_service.routes import api_router
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

    # Add CORS middleware
    cors_origins = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:4173",  # Vite preview server  
        "http://localhost:3000",  # Альтернативный порт
        "http://frontend:5173",   # Из Docker контейнера (локальная разработка)
    ]
    
    # Добавляем продакшен домены если настроены
    if hasattr(settings, 'frontend_url') and settings.frontend_url:
        cors_origins.extend([
            f"https://{settings.frontend_url}",
            f"https://www.{settings.frontend_url}",
            f"http://{settings.frontend_url}",
            f"http://www.{settings.frontend_url}",
        ])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add authentication and authorization middleware
    app.add_middleware(AuthMiddleware)

    app.include_router(api_router)
    app.include_router(user_management_router)
    
    # Add new permission and catalog management routes
    from warehouse_service.routes.permissions import router as permissions_router
    from warehouse_service.routes.catalog_management import router as catalog_router
    app.include_router(permissions_router)
    app.include_router(catalog_router)

    @app.get("/health", tags=["monitoring"], summary="Return service health status")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
