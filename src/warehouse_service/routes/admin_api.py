"""API routes for administrative functions - no HTML templates."""

from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from warehouse_service.auth import AuthService, CreateUserRequest
from warehouse_service.auth.dependencies import get_session
from warehouse_service.models.unified import (
    AppUser,
    Item,
    ItemGroup,
    Warehouse,
    WarehouseAccessGrant,
)

admin_api_router = APIRouter(prefix="/api/admin", tags=["admin-api"])


def get_current_user_from_request(request: Request) -> Optional[AppUser]:
    """Get current user from request state (set by middleware)."""
    return getattr(request.state, "user", None)


def ensure_system_admin(session: Session, request: Request) -> AppUser:
    """Ensure the current user is a system admin."""
    from warehouse_service.auth.permissions_v2 import require_system_admin
    
    current_user = get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    require_system_admin(session, current_user.app_user_id)
    return current_user


# ===== USER MANAGEMENT =====

@admin_api_router.get("/users", summary="List Users")
async def list_users(
    request: Request,
    session: Session = Depends(get_session),
):
    """Get list of all users with basic info."""
    ensure_system_admin(session, request)
    
    users = session.exec(select(AppUser)).all()
    return {
        "users": [
            {
                "app_user_id": str(user.app_user_id),
                "user_email": user.user_email,
                "user_display_name": user.user_display_name,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "last_login_at": user.last_login_at,
            }
            for user in users
        ]
    }


@admin_api_router.post("/users", summary="Create User")
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    session: Session = Depends(get_session),
):
    """Create a new user."""
    ensure_system_admin(session, request)
    
    auth_service = AuthService(session)
    try:
        user = auth_service.create_user(user_data)
        session.commit()
        
        return {
            "message": "User created successfully",
            "user_id": str(user.app_user_id),
            "email": user.user_email,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Email already exists")


@admin_api_router.get("/users/{user_id}", summary="Get User Details")
async def get_user_details(
    user_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """Get detailed information about a specific user."""
    ensure_system_admin(session, request)
    
    user = session.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "app_user_id": str(user.app_user_id),
        "user_email": user.user_email,
        "user_display_name": user.user_display_name,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
    }


@admin_api_router.delete("/users/{user_id}", summary="Delete User")
async def delete_user(
    user_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """Deactivate a user account."""
    current_admin = ensure_system_admin(session, request)
    
    user = session.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.app_user_id == current_admin.app_user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user.is_active = False
    session.commit()
    
    return {"message": f"User {user.user_email} has been deactivated"}


# ===== ITEM GROUP MANAGEMENT =====

@admin_api_router.get("/item-groups", summary="List Item Groups")
async def list_item_groups(
    request: Request,
    session: Session = Depends(get_session),
):
    """Get list of all item groups."""
    current_user = ensure_system_admin(session, request)
    
    item_groups = session.exec(select(ItemGroup)).all()
    return {
        "item_groups": [
            {
                "item_group_id": str(ig.item_group_id),
                "item_group_code": ig.item_group_code,
                "item_group_name": ig.item_group_name,
                "item_group_description": getattr(ig, 'item_group_description', None),
                "is_active": getattr(ig, 'is_active', True),
                "created_at": ig.created_at,
                "created_by": str(ig.created_by) if ig.created_by else None,
            }
            for ig in item_groups
        ]
    }


@admin_api_router.post("/item-groups", summary="Create Item Group")
async def create_item_group(
    request: Request,
    code: str,
    name: str,
    description: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Create a new item group."""
    current_user = ensure_system_admin(session, request)
    
    # Check if code already exists
    existing = session.exec(select(ItemGroup).where(ItemGroup.item_group_code == code)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item group code already exists")
    
    item_group = ItemGroup(
        item_group_code=code,
        item_group_name=name,
        created_by=current_user.app_user_id,
    )
    
    # Add description and is_active if they exist in the model
    if hasattr(item_group, 'item_group_description'):
        item_group.item_group_description = description
    if hasattr(item_group, 'is_active'):
        item_group.is_active = True
    
    session.add(item_group)
    session.commit()
    session.refresh(item_group)
    
    return {
        "message": "Item group created successfully",
        "item_group_id": str(item_group.item_group_id),
        "code": item_group.item_group_code,
        "name": item_group.item_group_name,
    }


@admin_api_router.get("/item-groups/{item_group_id}/items", summary="Get Items in Item Group")
async def get_items_in_group(
    item_group_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """Get all items in a specific item group."""
    ensure_system_admin(session, request)
    
    item_group = session.get(ItemGroup, item_group_id)
    if not item_group:
        raise HTTPException(status_code=404, detail="Item group not found")
    
    items = session.exec(select(Item).where(Item.item_group_id == item_group_id)).all()
    
    return {
        "item_group": {
            "id": str(item_group.item_group_id),
            "code": item_group.item_group_code,
            "name": item_group.item_group_name,
        },
        "items": [
            {
                "item_id": str(item.item_id),
                "stock_keeping_unit": item.stock_keeping_unit,
                "item_name": item.item_name,
                "unit_of_measure": item.unit_of_measure,
                "item_status": item.item_status,
                "is_lot_tracked": item.is_lot_tracked,
                "is_serial_number_tracked": item.is_serial_number_tracked,
            }
            for item in items
        ]
    }


# ===== WAREHOUSE MANAGEMENT =====

@admin_api_router.get("/warehouses", summary="List Warehouses")
async def list_warehouses(
    request: Request,
    session: Session = Depends(get_session),
):
    """Get list of all warehouses."""
    ensure_system_admin(session, request)
    
    warehouses = session.exec(select(Warehouse)).all()
    return {
        "warehouses": [
            {
                "warehouse_id": str(warehouse.warehouse_id),
                "warehouse_code": warehouse.warehouse_code,
                "warehouse_name": warehouse.warehouse_name,
                "warehouse_address": warehouse.warehouse_address,
                "time_zone": warehouse.time_zone,
                "is_active": warehouse.is_active,
                "created_at": warehouse.created_at,
                "created_by": str(warehouse.created_by) if warehouse.created_by else None,
            }
            for warehouse in warehouses
        ]
    }


# ===== ACCESS GRANTS MANAGEMENT =====

@admin_api_router.get("/users/{user_id}/grants", summary="Get User Access Grants")
async def get_user_grants(
    user_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """Get all access grants for a specific user."""
    ensure_system_admin(session, request)
    
    user = session.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    grants = session.exec(
        select(WarehouseAccessGrant).where(WarehouseAccessGrant.app_user_id == user_id)
    ).all()
    
    # Get related entity names
    warehouse_ids = {g.warehouse_id for g in grants}
    warehouse_info = {}
    if warehouse_ids:
        warehouses = session.exec(select(Warehouse).where(Warehouse.warehouse_id.in_(warehouse_ids))).all()
        warehouse_info = {str(w.warehouse_id): w for w in warehouses}
    
    return {
        "user_id": str(user_id),
        "user_email": user.user_email,
        "grants": [
            {
                "grant_id": str(grant.warehouse_access_grant_id),
                "warehouse_id": str(grant.warehouse_id),
                "warehouse_name": warehouse_info.get(str(grant.warehouse_id)).warehouse_name if warehouse_info.get(str(grant.warehouse_id)) else "Unknown",
                "scope_type": grant.scope_type,
                "scope_entity_identifier": str(grant.scope_entity_identifier) if grant.scope_entity_identifier else None,
                "can_read": grant.can_read,
                "can_write": grant.can_write,
                "can_approve": grant.can_approve,
            }
            for grant in grants
        ]
    }


@admin_api_router.post("/users/{user_id}/grants", summary="Create Access Grant")
async def create_access_grant(
    user_id: UUID,
    warehouse_id: UUID,
    scope_type: str,
    request: Request,
    scope_entity_identifier: Optional[UUID] = None,
    can_read: bool = True,
    can_write: bool = False,
    can_approved: bool = False,
    session: Session = Depends(get_session),
):
    """Create an access grant for a user."""
    current_admin = ensure_system_admin(session, request)
    
    user = session.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    warehouse = session.get(Warehouse, warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Check if grant already exists
    existing = session.exec(
        select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user_id,
            WarehouseAccessGrant.warehouse_id == warehouse_id,
            WarehouseAccessGrant.scope_type == scope_type,
            WarehouseAccessGrant.scope_entity_identifier == scope_entity_identifier,
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Access grant already exists")
    
    grant = WarehouseAccessGrant(
        app_user_id=user_id,
        warehouse_id=warehouse_id,
        scope_type=scope_type,
        scope_entity_identifier=scope_entity_identifier,
        can_read=can_read,
        can_write=can_write,
        can_approve=can_approved,
    )
    
    session.add(grant)
    session.commit()
    session.refresh(grant)
    
    return {
        "message": "Access grant created successfully",
        "grant_id": str(grant.warehouse_access_grant_id),
    }


@admin_api_router.delete("/grants/{grant_id}", summary="Delete Access Grant")
async def delete_access_grant(
    grant_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """Delete an access grant."""
    ensure_system_admin(session, request)
    
    grant = session.get(WarehouseAccessGrant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Access grant not found")
    
    session.delete(grant)
    session.commit()
    
    return {"message": "Access grant deleted successfully"}
