"""API routers."""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api")


@api_router.get("/status", tags=["monitoring"], summary="API status endpoint")
async def status() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["api_router"]
