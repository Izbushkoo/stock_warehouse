"""API routers."""

from __future__ import annotations

from fastapi import APIRouter

from .admin import admin_router
from .auth import auth_router
from .catalog import catalog_router
from .permissions import router as permissions_router
from .permissions_web import router as permissions_web_router
from .unified import router as unified_router
from .warehouses import warehouses_router
from .web import web_router

api_router = APIRouter()

# Include auth routes
api_router.include_router(auth_router)

# Include permissions routes
api_router.include_router(permissions_router)

# Include unified warehouse routes
api_router.include_router(unified_router)


@api_router.get("/status", tags=["monitoring"], summary="API status endpoint")
async def status() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["api_router", "admin_router", "catalog_router", "web_router", "permissions_web_router", "warehouses_router"]
