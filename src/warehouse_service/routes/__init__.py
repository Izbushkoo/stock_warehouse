"""API routers."""

from __future__ import annotations

from fastapi import APIRouter

# admin_api удален - используем новую систему разрешений
from .auth import auth_router
from .permissions import router as permissions_router
from .unified import router as unified_router

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


__all__ = ["api_router"]
