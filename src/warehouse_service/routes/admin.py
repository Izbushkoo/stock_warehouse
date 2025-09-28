"""Administrative views for unified warehouse RBAC management."""

from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from warehouse_service.auth import AuthService, CreateUserRequest
from warehouse_service.auth.dependencies import get_session
from warehouse_service.models.unified import (
    AppUser,
    BinLocation,
    ItemGroup,
    Warehouse,
    WarehouseAccessGrant,
    Zone,
)
from warehouse_service.rbac.unified import ScopeType

templates = Jinja2Templates(directory="src/warehouse_service/templates")
admin_router = APIRouter(prefix="/admin", tags=["admin"])

SCOPE_LABELS: Dict[ScopeType, str] = {
    ScopeType.WAREHOUSE: "Warehouse",
    ScopeType.ITEM_GROUP: "Item group",
    ScopeType.ZONE: "Zone",
    ScopeType.BIN_LOCATION: "Bin location",
}


def get_current_user_from_request(request: Request) -> Optional[AppUser]:
    """Get current user from request state (set by middleware)."""

    return getattr(request.state, "user", None)


def ensure_manage_users_permission(session: Session, request: Request) -> AppUser:
    """Ensure the current user can manage other users."""

    current_user = get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    has_permission = session.exec(
        select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == current_user.app_user_id,
            WarehouseAccessGrant.can_approve.is_(True),
        )
    ).first()

    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage users",
        )

    return current_user


def build_messages(request: Request) -> List[Dict[str, str]]:
    """Build flash messages from request query parameters."""

    message_text = request.query_params.get("message")
    if not message_text:
        return []

    status_param = request.query_params.get("status", "info")
    if status_param not in {"success", "error", "info"}:
        status_param = "info"

    return [
        {
            "text": message_text,
            "type": status_param,
        }
    ]


def redirect_with_message(url: str, message: str, status_value: str = "info") -> RedirectResponse:
    """Redirect with message query parameters preserved."""

    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query))
    query_params.update({"message": message, "status": status_value})

    new_query = urlencode(query_params)
    new_url = urlunparse(parsed._replace(query=new_query))
    return RedirectResponse(url=new_url, status_code=status.HTTP_303_SEE_OTHER)


def _resolve_entity_name(
    *,
    grant: WarehouseAccessGrant,
    warehouses: Dict[UUID, Warehouse],
    item_groups: Dict[UUID, ItemGroup],
    zones: Dict[UUID, Zone],
    bin_locations: Dict[UUID, BinLocation],
) -> str:
    """Resolve human readable entity name for access grant."""

    scope_type = ScopeType(grant.scope_type)
    if scope_type == ScopeType.WAREHOUSE:
        warehouse = warehouses.get(grant.warehouse_id)
        return warehouse.warehouse_name if warehouse else str(grant.warehouse_id)

    identifier = grant.scope_entity_identifier
    if not identifier:
        return "—"

    if scope_type == ScopeType.ITEM_GROUP:
        entity = item_groups.get(identifier)
        return entity.item_group_name if entity else str(identifier)
    if scope_type == ScopeType.ZONE:
        entity = zones.get(identifier)
        return entity.zone_name if entity else str(identifier)
    if scope_type == ScopeType.BIN_LOCATION:
        entity = bin_locations.get(identifier)
        return entity.bin_location_code if entity else str(identifier)

    return str(identifier)


@admin_router.get("/", response_class=HTMLResponse, summary="Admin Dashboard")
def admin_dashboard(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display administrative dashboard with quick statistics."""

    current_user = get_current_user_from_request(request)

    user_count = len(session.exec(select(AppUser)).all())
    warehouse_count = len(session.exec(select(Warehouse)).all())
    access_grant_count = len(session.exec(select(WarehouseAccessGrant)).all())

    recent_users = session.exec(
        select(AppUser).order_by(AppUser.created_at.desc()).limit(5)
    ).all()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": current_user,
            "messages": build_messages(request),
            "stats": {
                "users": user_count,
                "warehouses": warehouse_count,
                "access_grants": access_grant_count,
            },
            "recent_users": recent_users,
        },
    )


@admin_router.get("/users", response_class=HTMLResponse, summary="List Users")
def list_users(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """List application users with management actions."""

    current_user = ensure_manage_users_permission(session, request)
    auth_service = AuthService(session)
    users = auth_service.list_users()

    user_rows: List[Dict[str, object]] = []
    for user in users:
        grants = session.exec(
            select(WarehouseAccessGrant).where(
                WarehouseAccessGrant.app_user_id == user.app_user_id
            )
        ).all()

        user_rows.append(
            {
                "id": user.app_user_id,
                "email": user.user_email,
                "display_name": user.user_display_name,
                "is_active": user.is_active,
                "grant_count": len(grants),
                "last_login": user.last_login_at,
                "created_at": user.created_at,
                "password_hash": user.password_hash,
            }
        )

    return templates.TemplateResponse(
        "admin/users/list.html",
        {
            "request": request,
            "user": current_user,
            "messages": build_messages(request),
            "users": user_rows,
        },
    )


@admin_router.post("/users/create", summary="Create User")
async def create_user(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    is_active: bool = Form(False),
    session: Session = Depends(get_session),
):
    """Create a new application user."""

    ensure_manage_users_permission(session, request)
    auth_service = AuthService(session)

    try:
        auth_service.create_user(
            CreateUserRequest(
                email=email.strip(),
                display_name=display_name.strip(),
                password=password,
                is_active=is_active,
            )
        )
    except ValueError as exc:  # duplicate email etc.
        return redirect_with_message("/admin/users", str(exc), "error")

    return redirect_with_message("/admin/users", "User created successfully", "success")


@admin_router.post("/users/{user_id}/update", summary="Update User")
async def update_user(
    request: Request,
    user_id: UUID,
    email: str = Form(...),
    display_name: str = Form(...),
    is_active: bool = Form(False),
    new_password: Optional[str] = Form(default=None),
    session: Session = Depends(get_session),
):
    """Update user profile and optionally reset password."""

    ensure_manage_users_permission(session, request)
    auth_service = AuthService(session)

    password_value = (new_password or "").strip() or None

    try:
        auth_service.update_user(
            user_id,
            email=email.strip(),
            display_name=display_name.strip(),
            is_active=is_active,
            password=password_value,
        )
    except ValueError as exc:
        return redirect_with_message(
            f"/admin/users/{user_id}",
            str(exc),
            "error",
        )

    message = "User updated successfully"
    if password_value:
        message = "User updated and password reset"

    return redirect_with_message(f"/admin/users/{user_id}", message, "success")


@admin_router.post("/users/{user_id}/delete", summary="Delete User")
async def delete_user(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete user and associated grants."""

    current_user = ensure_manage_users_permission(session, request)

    if current_user.app_user_id == user_id:
        return redirect_with_message(
            "/admin/users",
            "You cannot delete your own account",
            "error",
        )

    auth_service = AuthService(session)

    try:
        auth_service.delete_user(user_id)
    except ValueError as exc:
        return redirect_with_message(
            f"/admin/users/{user_id}",
            str(exc),
            "error",
        )

    return redirect_with_message("/admin/users", "User removed", "success")


@admin_router.get("/users/{user_id}", response_class=HTMLResponse, summary="User Detail")
def user_detail(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display detail view for specific user."""

    current_user = ensure_manage_users_permission(session, request)
    auth_service = AuthService(session)
    user = auth_service.get_user(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    warehouses = {
        warehouse.warehouse_id: warehouse
        for warehouse in session.exec(select(Warehouse)).all()
    }
    item_groups = {
        group.item_group_id: group
        for group in session.exec(select(ItemGroup)).all()
    }
    zones = {zone.zone_id: zone for zone in session.exec(select(Zone)).all()}
    bin_locations = {
        bin_location.bin_location_id: bin_location
        for bin_location in session.exec(select(BinLocation)).all()
    }

    grants = session.exec(
        select(WarehouseAccessGrant)
        .where(WarehouseAccessGrant.app_user_id == user.app_user_id)
        .order_by(WarehouseAccessGrant.warehouse_id, WarehouseAccessGrant.scope_type)
    ).all()

    grant_rows = []
    for grant in grants:
        warehouse_obj = warehouses.get(grant.warehouse_id)
        scope = ScopeType(grant.scope_type)
        permissions = {
            "read": grant.can_read,
            "write": grant.can_write,
            "approve": grant.can_approve,
        }
        grant_rows.append(
            {
                "id": grant.warehouse_access_grant_id,
                "warehouse_name": warehouse_obj.warehouse_name if warehouse_obj else str(grant.warehouse_id),
                "scope_type": scope,
                "scope_label": SCOPE_LABELS.get(scope, scope.value.title()),
                "entity_name": _resolve_entity_name(
                    grant=grant,
                    warehouses=warehouses,
                    item_groups=item_groups,
                    zones=zones,
                    bin_locations=bin_locations,
                ),
                "permissions": permissions,
            }
        )

    scope_options = [
        {"value": scope.value, "label": label}
        for scope, label in SCOPE_LABELS.items()
    ]

    return templates.TemplateResponse(
        "admin/users/detail.html",
        {
            "request": request,
            "user": current_user,
            "messages": build_messages(request),
            "subject": user,
            "grants": grant_rows,
            "warehouses": list(warehouses.values()),
            "item_groups": list(item_groups.values()),
            "zones": list(zones.values()),
            "bin_locations": list(bin_locations.values()),
            "scope_options": scope_options,
        },
    )


@admin_router.post("/users/{user_id}/grants/add", summary="Add Access Grant")
async def add_access_grant(
    request: Request,
    user_id: UUID,
    warehouse_id: UUID = Form(...),
    scope_type: str = Form(...),
    scope_entity_identifier: Optional[str] = Form(default=None),
    can_read: bool = Form(False),
    can_write: bool = Form(False),
    can_approve: bool = Form(False),
    session: Session = Depends(get_session),
):
    """Add new access grant for user."""

    ensure_manage_users_permission(session, request)

    try:
        scope = ScopeType(scope_type)
    except ValueError:
        return redirect_with_message(
            f"/admin/users/{user_id}",
            "Unknown scope type",
            "error",
        )

    user = session.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    entity_identifier: Optional[UUID] = None
    if scope == ScopeType.WAREHOUSE:
        entity_identifier = warehouse_id
    else:
        if not scope_entity_identifier:
            return redirect_with_message(
                f"/admin/users/{user_id}",
                "Scope entity is required for the selected type",
                "error",
            )
        try:
            entity_identifier = UUID(scope_entity_identifier)
        except ValueError:
            return redirect_with_message(
                f"/admin/users/{user_id}",
                "Invalid scope entity identifier",
                "error",
            )

    grant = WarehouseAccessGrant(
        app_user_id=user.app_user_id,
        warehouse_id=warehouse_id,
        scope_type=scope.value,
        scope_entity_identifier=entity_identifier,
        can_read=can_read,
        can_write=can_write,
        can_approve=can_approve,
    )

    session.add(grant)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return redirect_with_message(
            f"/admin/users/{user_id}",
            "Такой грант уже существует",
            "error",
        )
    except Exception as exc:  # pragma: no cover - commit errors handled uniformly
        session.rollback()
        return redirect_with_message(
            f"/admin/users/{user_id}",
            f"Unable to add access grant: {exc}",
            "error",
        )

    return redirect_with_message(
        f"/admin/users/{user_id}",
        "Access grant added",
        "success",
    )


@admin_router.post(
    "/users/{user_id}/grants/{grant_id}/delete",
    summary="Delete Access Grant",
)
async def delete_access_grant(
    request: Request,
    user_id: UUID,
    grant_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete user access grant."""

    ensure_manage_users_permission(session, request)

    grant = session.get(WarehouseAccessGrant, grant_id)
    if not grant:
        return redirect_with_message(
            f"/admin/users/{user_id}",
            "Access grant not found",
            "error",
        )

    session.delete(grant)
    session.commit()

    return redirect_with_message(
        f"/admin/users/{user_id}",
        "Access grant removed",
        "success",
    )


@admin_router.get("/permissions", response_class=HTMLResponse, summary="Permissions Overview")
def permissions_overview(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display permissions overview per user and warehouse."""

    current_user = ensure_manage_users_permission(session, request)

    users = session.exec(select(AppUser).order_by(AppUser.user_email)).all()
    warehouses = {
        warehouse.warehouse_id: warehouse
        for warehouse in session.exec(select(Warehouse)).all()
    }
    item_groups = {
        group.item_group_id: group
        for group in session.exec(select(ItemGroup)).all()
    }
    zones = {zone.zone_id: zone for zone in session.exec(select(Zone)).all()}
    bin_locations = {
        bin_location.bin_location_id: bin_location
        for bin_location in session.exec(select(BinLocation)).all()
    }

    user_summaries: List[Dict[str, object]] = []
    for user in users:
        grants = session.exec(
            select(WarehouseAccessGrant).where(
                WarehouseAccessGrant.app_user_id == user.app_user_id
            )
        ).all()

        warehouse_groups: Dict[UUID, List[WarehouseAccessGrant]] = {}
        for grant in grants:
            warehouse_groups.setdefault(grant.warehouse_id, []).append(grant)

        warehouses_summary: List[Dict[str, object]] = []
        for warehouse_id, warehouse_grants in warehouse_groups.items():
            warehouse = warehouses.get(warehouse_id)
            scope_data = []
            for grant in warehouse_grants:
                scope = ScopeType(grant.scope_type)
                scope_data.append(
                    {
                        "scope_label": SCOPE_LABELS.get(scope, scope.value.title()),
                        "entity_name": _resolve_entity_name(
                            grant=grant,
                            warehouses=warehouses,
                            item_groups=item_groups,
                            zones=zones,
                            bin_locations=bin_locations,
                        ),
                        "permissions": {
                            "read": grant.can_read,
                            "write": grant.can_write,
                            "approve": grant.can_approve,
                        },
                    }
                )

            warehouses_summary.append(
                {
                    "id": warehouse_id,
                    "name": warehouse.warehouse_name if warehouse else str(warehouse_id),
                    "scopes": scope_data,
                }
            )

        user_summaries.append(
            {
                "id": user.app_user_id,
                "email": user.user_email,
                "display_name": user.user_display_name,
                "is_active": user.is_active,
                "warehouses": warehouses_summary,
                "grant_count": len(grants),
            }
        )

    return templates.TemplateResponse(
        "admin/permissions/overview.html",
        {
            "request": request,
            "user": current_user,
            "messages": build_messages(request),
            "users": user_summaries,
        },
    )


@admin_router.get("/warehouses", response_class=HTMLResponse, summary="List Warehouses")
def list_warehouses(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display warehouses overview."""

    current_user = get_current_user_from_request(request)
    warehouses = session.exec(select(Warehouse).order_by(Warehouse.warehouse_name)).all()

    return templates.TemplateResponse(
        "admin/warehouses/list.html",
        {
            "request": request,
            "user": current_user,
            "messages": build_messages(request),
            "warehouses": warehouses,
        },
    )


__all__ = ["admin_router"]
