"""API routes for permission management."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from warehouse_service.auth.dependencies import get_current_user, get_session
from warehouse_service.auth.permissions_v2 import (
    PermissionManager, ResourceType, PermissionLevel,
    require_system_admin, require_item_group_permission, require_warehouse_permission
)
from warehouse_service.models.unified import AppUser, ItemGroup, Warehouse

router = APIRouter(prefix="/api/permissions", tags=["Permissions"])


class GrantPermissionRequest(BaseModel):
    """Request to grant permission to user."""
    user_id: UUID
    resource_type: ResourceType
    resource_id: UUID
    permission_level: PermissionLevel
    expires_at: Optional[str] = None


class RevokePermissionRequest(BaseModel):
    """Request to revoke permission from user."""
    user_id: UUID
    resource_type: ResourceType
    resource_id: UUID


class UserPermissionSummary(BaseModel):
    """Summary of user permissions."""
    user_id: str
    user_email: str
    user_name: str
    is_system_admin: bool
    item_groups: Dict[str, Dict[str, Any]]
    warehouses: Dict[str, Dict[str, Any]]


@router.post("/grant")
async def grant_permission(
    request: GrantPermissionRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Grant permission to user for specific resource."""
    pm = PermissionManager(session)
    
    try:
        expires_at = None
        if request.expires_at:
            from datetime import datetime
            expires_at = datetime.fromisoformat(request.expires_at)
        
        permission = pm.grant_permission(
            user_id=request.user_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            permission_level=request.permission_level,
            granted_by=current_user.app_user_id,
            expires_at=expires_at
        )
        
        session.commit()
        
        return {
            "success": True,
            "message": f"Permission {request.permission_level.value} granted for {request.resource_type.value}",
            "permission_id": str(permission.permission_id)
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/revoke")
async def revoke_permission(
    request: RevokePermissionRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Revoke permission from user for specific resource."""
    pm = PermissionManager(session)
    
    try:
        success = pm.revoke_permission(
            user_id=request.user_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            revoked_by=current_user.app_user_id
        )
        
        session.commit()
        
        if success:
            return {
                "success": True,
                "message": f"Permission revoked for {request.resource_type.value}"
            }
        else:
            return {
                "success": False,
                "message": "Permission not found or already revoked"
            }
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/test")
async def test_permissions_endpoint(
    current_user: AppUser = Depends(get_current_user)
):
    """Test endpoint to verify permissions API is working."""
    return {
        "message": "Permissions API is working",
        "user_id": str(current_user.app_user_id),
        "user_email": current_user.user_email
    }


@router.get("/user/{user_id}")
async def get_user_permissions(
    user_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> UserPermissionSummary:
    """Get comprehensive permissions summary for user."""
    
    # Check if current user can view this user's permissions
    if user_id != current_user.app_user_id:
        pm = PermissionManager(session)
        if not pm.is_system_admin(current_user.app_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view your own permissions"
            )
    
    # Get target user
    target_user = session.get(AppUser, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    pm = PermissionManager(session)
    
    # Get system admin status
    is_system_admin = pm.is_system_admin(user_id)
    
    # Get item group permissions
    item_groups = {}
    item_group_permissions = pm.get_user_permissions(user_id)
    
    for perm in item_group_permissions:
        if perm["resource_type"] == ResourceType.ITEM_GROUP.value:
            item_group = session.get(ItemGroup, UUID(perm["resource_id"]))
            if item_group:
                item_groups[perm["resource_id"]] = {
                    "item_group_id": perm["resource_id"],
                    "item_group_name": item_group.item_group_name,
                    "permission_level": perm["permission_level"],
                    "granted_at": perm["granted_at"],
                    "expires_at": perm["expires_at"]
                }
    
    # Get warehouse permissions (including inherited)
    warehouses = pm.get_user_warehouse_permissions(user_id)
    
    return UserPermissionSummary(
        user_id=str(user_id),
        user_email=target_user.user_email,
        user_name=target_user.user_display_name,
        is_system_admin=is_system_admin,
        item_groups=item_groups,
        warehouses=warehouses
    )


@router.get("/item-groups")
async def list_accessible_item_groups(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List all item groups accessible to current user."""
    pm = PermissionManager(session)
    item_groups = pm.get_user_item_groups(current_user.app_user_id)
    
    return [
        {
            "item_group_id": str(ig.item_group_id),
            "item_group_code": ig.item_group_code,
            "item_group_name": ig.item_group_name,
            "item_group_description": ig.item_group_description
        }
        for ig in item_groups
    ]


@router.get("/warehouses")
async def list_accessible_warehouses(
    item_group_id: Optional[UUID] = None,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List all warehouses accessible to current user."""
    pm = PermissionManager(session)
    warehouses = pm.get_user_warehouses(current_user.app_user_id, item_group_id)
    
    return [
        {
            "warehouse_id": str(w.warehouse_id),
            "warehouse_code": w.warehouse_code,
            "warehouse_name": w.warehouse_name,
            "warehouse_address": w.warehouse_address,
            "item_group_id": str(w.item_group_id),
            "is_active": w.is_active
        }
        for w in warehouses
    ]


@router.get("/warehouses/writable")
async def list_writable_warehouses(
    item_group_id: Optional[UUID] = None,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List warehouses where current user can write (add/remove inventory)."""
    pm = PermissionManager(session)
    writable_ids = pm.get_writable_warehouse_ids(current_user.app_user_id, item_group_id)
    
    if not writable_ids:
        return []
    
    from sqlmodel import select
    warehouses = session.exec(
        select(Warehouse).where(Warehouse.warehouse_id.in_(writable_ids))
    ).all()
    
    return [
        {
            "warehouse_id": str(w.warehouse_id),
            "warehouse_code": w.warehouse_code,
            "warehouse_name": w.warehouse_name,
            "warehouse_address": w.warehouse_address,
            "item_group_id": str(w.item_group_id),
            "is_active": w.is_active
        }
        for w in warehouses
    ]


@router.get("/check/warehouse/{warehouse_id}")
async def check_warehouse_permission(
    warehouse_id: UUID,
    permission_level: PermissionLevel,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Check if current user has specific permission level for warehouse."""
    pm = PermissionManager(session)
    
    has_permission = pm.has_warehouse_permission(
        current_user.app_user_id, 
        warehouse_id, 
        permission_level
    )
    
    return {
        "warehouse_id": str(warehouse_id),
        "permission_level": permission_level.value,
        "has_permission": has_permission
    }


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_permissions(
    resource_type: ResourceType,
    resource_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all users with permissions for specific resource."""
    
    # Check if current user can view permissions for this resource
    pm = PermissionManager(session)
    
    if resource_type == ResourceType.ITEM_GROUP:
        require_item_group_permission(current_user, session, resource_id, PermissionLevel.ADMIN)
    elif resource_type == ResourceType.WAREHOUSE:
        require_warehouse_permission(current_user, session, resource_id, PermissionLevel.ADMIN)
    elif resource_type == ResourceType.SYSTEM:
        require_system_admin(current_user, session)
    
    permissions = pm.get_resource_permissions(resource_type, resource_id)
    
    return {
        "resource_type": resource_type.value,
        "resource_id": str(resource_id),
        "permissions": permissions
    }