"""Web interface routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from warehouse_service.models.unified import AppUser

web_router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="src/warehouse_service/templates")


def get_current_user_from_request(request: Request) -> AppUser:
    """Get current user from request state (set by middleware)."""
    return getattr(request.state, 'user', None)


def build_messages(request: Request) -> list[dict[str, str]]:
    """Extract flash messages from query parameters."""

    message = request.query_params.get("message")
    if not message:
        return []

    status = request.query_params.get("status", "info")
    if status not in {"success", "error", "info"}:
        status = "info"
    return [{"text": message, "type": status}]


@web_router.get("/", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str = None
):
    """Login page."""
    user = get_current_user_from_request(request)

    # If user is already logged in, redirect to admin
    if user:
        return RedirectResponse(url="/admin", status_code=302)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
            "messages": build_messages(request),
        }
    )


@web_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""

    user = get_current_user_from_request(request)
    if user:
        return RedirectResponse(url="/admin", status_code=302)

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "messages": build_messages(request),
        }
    )


__all__ = ["web_router"]