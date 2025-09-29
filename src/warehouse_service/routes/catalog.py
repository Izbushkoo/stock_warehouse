"""Catalog views for browsing available item groups (inventories)."""

from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from warehouse_service.auth.dependencies import get_session
from warehouse_service.models.unified import (
    AppUser,
    Item,
    ItemGroup,
    Warehouse,
    WarehouseAccessGrant,
)
from warehouse_service.rbac.unified import ScopeType

templates = Jinja2Templates(directory="src/warehouse_service/templates")
catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_current_user_from_request(request: Request) -> Optional[AppUser]:
    """Get current user from request state (set by middleware)."""
    return getattr(request.state, "user", None)


def get_user_accessible_item_groups(session: Session, user: AppUser) -> List[ItemGroup]:
    """Get item groups that user has access to through warehouse grants."""
    
    # Get all warehouse access grants for the user
    grants = session.exec(
        select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user.app_user_id,
            WarehouseAccessGrant.can_read == True
        )
    ).all()
    
    # Get unique warehouse IDs from grants
    warehouse_ids = list(set(grant.warehouse_id for grant in grants))
    
    if not warehouse_ids:
        return []
    
    # Get warehouses and their item groups
    warehouses = session.exec(
        select(Warehouse).where(
            Warehouse.warehouse_id.in_(warehouse_ids),
            Warehouse.is_active == True
        )
    ).all()
    
    # Get unique item group IDs
    item_group_ids = list(set(warehouse.item_group_id for warehouse in warehouses if warehouse.item_group_id))
    
    if not item_group_ids:
        return []
    
    # Get item groups
    item_groups = session.exec(
        select(ItemGroup).where(
            ItemGroup.item_group_id.in_(item_group_ids),
            ItemGroup.is_active == True
        ).order_by(ItemGroup.item_group_name)
    ).all()
    
    return item_groups


@catalog_router.get("/", response_class=HTMLResponse, summary="Catalog Overview")
def catalog_overview(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display catalog overview with available item groups."""
    
    current_user = get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    
    # Get accessible item groups
    item_groups = get_user_accessible_item_groups(session, current_user)
    
    # Get statistics for each item group
    item_group_stats = []
    for item_group in item_groups:
        # Count items in this item group
        item_count = len(session.exec(
            select(Item).where(
                Item.item_group_id == item_group.item_group_id,
                Item.item_status == "active"
            )
        ).all())
        
        # Count warehouses in this item group
        warehouse_count = len(session.exec(
            select(Warehouse).where(
                Warehouse.item_group_id == item_group.item_group_id,
                Warehouse.is_active == True
            )
        ).all())
        
        item_group_stats.append({
            "item_group": item_group,
            "item_count": item_count,
            "warehouse_count": warehouse_count,
            "description": getattr(item_group, 'item_group_description', None),
        })
    
    return templates.TemplateResponse(
        "catalog/overview.html",
        {
            "request": request,
            "user": current_user,
            "item_groups": item_group_stats,
        },
    )


@catalog_router.get("/{item_group_id}", response_class=HTMLResponse, summary="Item Group Catalog")
def item_group_catalog(
    request: Request,
    item_group_id: UUID,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display items in specific item group catalog."""
    
    current_user = get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    
    # Check if user has access to this item group
    accessible_item_groups = get_user_accessible_item_groups(session, current_user)
    accessible_item_group_ids = [ig.item_group_id for ig in accessible_item_groups]
    
    if item_group_id not in accessible_item_group_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this catalog")
    
    # Get the item group
    item_group = session.get(ItemGroup, item_group_id)
    if not item_group or not item_group.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not found")
    
    # Get items in this item group
    items_query = session.exec(
        select(Item)
        .where(
            Item.item_group_id == item_group_id,
            Item.item_status == "active"
        )
        .order_by(Item.item_name)
    ).all()
    
    # Get warehouses in this item group for context
    warehouses_in_group = session.exec(
        select(Warehouse).where(
            Warehouse.item_group_id == item_group_id,
            Warehouse.is_active == True
        ).order_by(Warehouse.warehouse_name)
    ).all()
    
    # Format items for display
    items = []
    for item in items_query:
        items.append({
            "id": item.item_id,
            "name": item.item_name,
            "sku": item.stock_keeping_unit,
            "description": getattr(item, 'item_description', ''),  # Fallback if field doesn't exist
            "unit_of_measure": item.unit_of_measure,
            "barcode": item.barcode_value,
            "is_lot_tracked": item.is_lot_tracked,
            "is_serial_tracked": item.is_serial_number_tracked,
            "created_at": item.created_at,
        })
    
    # Use warehouses from above
    warehouses = warehouses_in_group
    
    return templates.TemplateResponse(
        "catalog/item_group.html",
        {
            "request": request,
            "user": current_user,
            "item_group": item_group,
            "items": items,
            "warehouses": warehouses,
        },
    )


__all__ = ["catalog_router"]