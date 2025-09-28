"""Web interface routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from warehouse_service.models.unified import AppUser

web_router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="src/warehouse_service/templates")


def get_current_user_from_request(request: Request) -> AppUser:
    """Get current user from request state (set by middleware)."""
    return getattr(request.state, 'user', None)


@web_router.get("/", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str = None
):
    """Login page."""
    user = get_current_user_from_request(request)
    
    # If user is already logged in, redirect to admin
    if user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin", status_code=302)
    
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request,
            "error": error
        }
    )


__all__ = ["web_router"]