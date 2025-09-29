"""Warehouse views for regular users with inventory access."""

from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from warehouse_service.auth.dependencies import get_session
from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType, PermissionLevel
from warehouse_service.models.unified import (
    AppUser,
    Item,
    ItemGroup,
    Warehouse,
)

templates = Jinja2Templates(directory="src/warehouse_service/templates")
warehouses_router = APIRouter(prefix="/warehouses", tags=["warehouses"])


def get_current_user_from_request(request: Request) -> Optional[AppUser]:
    """Get current user from request state (set by middleware)."""
    return getattr(request.state, "user", None)


@warehouses_router.get("/", response_class=HTMLResponse, summary="Warehouses Overview")
def warehouses_overview(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display warehouses that user has access to."""

    current_user = get_current_user_from_request(request)
    if not current_user:
        # This should be handled by middleware, but just in case
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    pm = PermissionManager(session)
    
    # Get warehouses user has access to
    user_warehouses = pm.get_user_warehouses(current_user.app_user_id)
    
    # Get warehouse statistics
    warehouse_stats = []
    for warehouse in user_warehouses:
        # Count items in this warehouse
        item_count = len(session.exec(
            select(Item).where(Item.warehouse_id == warehouse.warehouse_id)
        ).all())
        
        # Get item group info
        item_group = session.get(ItemGroup, warehouse.item_group_id)
        
        warehouse_stats.append({
            "warehouse": warehouse,
            "item_group": item_group,
            "item_count": item_count,
            "user_permissions": pm.get_user_permissions(current_user.app_user_id)
        })

    return templates.TemplateResponse(
        "warehouses/overview.html",
        {
            "request": request,
            "user": current_user,
            "warehouse_stats": warehouse_stats,
            "is_system_admin": pm.is_system_admin(current_user.app_user_id),
        },
    )


@warehouses_router.get("/{warehouse_id}", response_class=HTMLResponse, summary="Warehouse Detail")
def warehouse_detail(
    request: Request,
    warehouse_id: UUID,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display detailed view of a specific warehouse."""

    current_user = get_current_user_from_request(request)
    if not current_user:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    pm = PermissionManager(session)
    
    # Check if user has access to this warehouse
    if not pm.has_permission(current_user.app_user_id, ResourceType.WAREHOUSE, warehouse_id, PermissionLevel.READ):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this warehouse")

    # Get warehouse info
    warehouse = session.get(Warehouse, warehouse_id)
    if not warehouse:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    # Get item group info
    item_group = session.get(ItemGroup, warehouse.item_group_id)
    
    # Get items in this warehouse
    items = session.exec(
        select(Item).where(Item.warehouse_id == warehouse_id).order_by(Item.item_name)
    ).all()

    # Get user permissions for this warehouse
    user_permissions = pm.get_user_permissions(current_user.app_user_id)
    warehouse_permissions = [
        perm for perm in user_permissions 
        if perm["resource_type"] == ResourceType.WAREHOUSE.value and perm["resource_id"] == str(warehouse_id)
    ]

    return templates.TemplateResponse(
        "warehouses/detail.html",
        {
            "request": request,
            "user": current_user,
            "warehouse": warehouse,
            "item_group": item_group,
            "items": items,
            "warehouse_permissions": warehouse_permissions,
            "is_system_admin": pm.is_system_admin(current_user.app_user_id),
        },
    )


__all__ = ["warehouses_router"]