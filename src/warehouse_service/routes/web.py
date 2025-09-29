"""Web interface routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from warehouse_service.db import session_scope
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

    # If user is already logged in, redirect based on permissions
    if user:
        with session_scope() as session:
            from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType
            pm = PermissionManager(session)
            
            if pm.is_system_admin(user.app_user_id):
                return RedirectResponse(url="/admin", status_code=302)
            else:
                # Check if user has warehouse access
                user_permissions = pm.get_user_permissions(user.app_user_id)
                has_warehouse_access = any(
                    perm["resource_type"] == ResourceType.WAREHOUSE.value 
                    for perm in user_permissions
                )
                
                if has_warehouse_access:
                    return RedirectResponse(url="/warehouses", status_code=302)
                else:
                    # User has no permissions, show error
                    return templates.TemplateResponse(
                        "login.html",
                        {
                            "request": request,
                            "error": "У вас нет доступа к системе. Обратитесь к администратору.",
                            "messages": build_messages(request),
                        }
                    )

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
            "messages": build_messages(request),
        }
    )


@web_router.post("/login")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Handle login form submission."""
    from warehouse_service.auth.auth_service import AuthService
    from warehouse_service.auth.models import LoginRequest
    from warehouse_service.db import session_scope
    
    with session_scope() as session:
        auth_service = AuthService(session)
        token_response = auth_service.login(LoginRequest(email=email, password=password))
        
        if not token_response:
            return RedirectResponse(url="/?error=invalid_credentials", status_code=302)
        
        # Create response with redirect
        response = RedirectResponse(url="/admin", status_code=302)
        
        # Set cookie with token
        response.set_cookie(
            key="access_token",
            value=token_response.access_token,
            max_age=86400,  # 24 hours
            httponly=False,  # Allow JavaScript access
            secure=False,    # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return response


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