"""API routes for permission management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from warehouse_service.auth.dependencies import get_current_user, get_session
from warehouse_service.auth.permissions_v2 import (
    PermissionManager, ResourceType, PermissionLevel,
    require_system_admin, require_item_group_permission, require_warehouse_permission
)
from warehouse_service.models.unified import AppUser, ItemGroup, Warehouse


router = APIRouter(prefix="/api/permissions", tags=["permissions"])


# Pydantic models for API
class GrantPermissionRequest(BaseModel):
    user_email: EmailStr
    permission_level: PermissionLevel
    expires_at: Optional[str] = None


class PermissionResponse(BaseModel):
    user_id: str
    user_email: str
    user_name: str
    permission_level: str
    granted_at: str
    expires_at: Optional[str] = None


class UserPermissionSummary(BaseModel):
    resource_type: str
    resource_id: str
    permission_level: str
    granted_at: str
    expires_at: Optional[str] = None


class ItemGroupResponse(BaseModel):
    item_group_id: str
    item_group_code: str
    item_group_name: str
    permission_level: Optional[str] = None


class WarehouseResponse(BaseModel):
    warehouse_id: str
    warehouse_code: str
    warehouse_name: str
    item_group_id: str
    permission_level: Optional[str] = None


# System admin routes
@router.post("/item-groups", summary="Create Item Group (System Admin Only)")
def create_item_group(
    item_group_code: str,
    item_group_name: str,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create new item group. Only system administrators can create item groups."""
    
    require_system_admin(current_user, session)
    
    # Check if code already exists
    existing = session.exec(
        select(ItemGroup).where(ItemGroup.item_group_code == item_group_code)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item group with code '{item_group_code}' already exists"
        )
    
    # Create item group
    item_group = ItemGroup(
        item_group_code=item_group_code,
        item_group_name=item_group_name,
        created_by=current_user.app_user_id
    )
    
    session.add(item_group)
    session.commit()
    session.refresh(item_group)
    
    # Grant owner permission to creator
    pm = PermissionManager(session)
    pm.grant_permission(
        user_id=current_user.app_user_id,
        resource_type=ResourceType.ITEM_GROUP,
        resource_id=item_group.item_group_id,
        permission_level=PermissionLevel.OWNER,
        granted_by=current_user.app_user_id
    )
    session.commit()
    
    return {
        "item_group_id": str(item_group.item_group_id),
        "item_group_code": item_group.item_group_code,
        "item_group_name": item_group.item_group_name,
        "message": "Item group created successfully"
    }


@router.get("/item-groups", response_model=List[ItemGroupResponse], summary="List User's Item Groups")
def list_user_item_groups(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> List[ItemGroupResponse]:
    """Get all item groups user has access to."""
    
    pm = PermissionManager(session)
    item_groups = pm.get_user_item_groups(current_user.app_user_id)
    
    result = []
    for ig in item_groups:
        # Get user's permission level for this item group
        permission_level = None
        if pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, ig.item_group_id, PermissionLevel.READ):
            if pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, ig.item_group_id, PermissionLevel.OWNER):
                permission_level = "owner"
            elif pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, ig.item_group_id, PermissionLevel.ADMIN):
                permission_level = "admin"
            elif pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, ig.item_group_id, PermissionLevel.WRITE):
                permission_level = "write"
            else:
                permission_level = "read"
        
        result.append(ItemGroupResponse(
            item_group_id=str(ig.item_group_id),
            item_group_code=ig.item_group_code,
            item_group_name=ig.item_group_name,
            permission_level=permission_level
        ))
    
    return result


# Item group management routes
@router.post("/item-groups/{item_group_id}/warehouses", summary="Create Warehouse in Item Group")
def create_warehouse(
    item_group_id: UUID,
    warehouse_code: str,
    warehouse_name: str,
    warehouse_address: Optional[str] = None,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create warehouse in item group. Requires write permission on item group."""
    
    require_item_group_permission(current_user, session, item_group_id, PermissionLevel.WRITE)
    
    # Check if code already exists
    existing = session.exec(
        select(Warehouse).where(Warehouse.warehouse_code == warehouse_code)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Warehouse with code '{warehouse_code}' already exists"
        )
    
    # Create warehouse
    warehouse = Warehouse(
        warehouse_code=warehouse_code,
        warehouse_name=warehouse_name,
        warehouse_address=warehouse_address,
        item_group_id=item_group_id,
        created_by=current_user.app_user_id
    )
    
    session.add(warehouse)
    session.commit()
    session.refresh(warehouse)
    
    # Grant admin permission to creator
    pm = PermissionManager(session)
    pm.grant_permission(
        user_id=current_user.app_user_id,
        resource_type=ResourceType.WAREHOUSE,
        resource_id=warehouse.warehouse_id,
        permission_level=PermissionLevel.ADMIN,
        granted_by=current_user.app_user_id
    )
    session.commit()
    
    return {
        "warehouse_id": str(warehouse.warehouse_id),
        "warehouse_code": warehouse.warehouse_code,
        "warehouse_name": warehouse.warehouse_name,
        "message": "Warehouse created successfully"
    }


@router.get("/item-groups/{item_group_id}/warehouses", response_model=List[WarehouseResponse], summary="List Warehouses in Item Group")
def list_item_group_warehouses(
    item_group_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> List[WarehouseResponse]:
    """Get all warehouses in item group user has access to."""
    
    require_item_group_permission(current_user, session, item_group_id, PermissionLevel.READ)
    
    pm = PermissionManager(session)
    warehouses = pm.get_user_warehouses(current_user.app_user_id, item_group_id)
    
    result = []
    for w in warehouses:
        # Get user's permission level for this warehouse
        permission_level = None
        if pm.has_permission(current_user.app_user_id, ResourceType.WAREHOUSE, w.warehouse_id, PermissionLevel.READ):
            if pm.has_permission(current_user.app_user_id, ResourceType.WAREHOUSE, w.warehouse_id, PermissionLevel.ADMIN):
                permission_level = "admin"
            elif pm.has_permission(current_user.app_user_id, ResourceType.WAREHOUSE, w.warehouse_id, PermissionLevel.WRITE):
                permission_level = "write"
            else:
                permission_level = "read"
        
        result.append(WarehouseResponse(
            warehouse_id=str(w.warehouse_id),
            warehouse_code=w.warehouse_code,
            warehouse_name=w.warehouse_name,
            item_group_id=str(w.item_group_id),
            permission_level=permission_level
        ))
    
    return result


@router.post("/item-groups/{item_group_id}/grant", summary="Grant Item Group Permission")
def grant_item_group_permission(
    item_group_id: UUID,
    request: GrantPermissionRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Grant permission on item group to user by email. Requires admin permission."""
    
    require_item_group_permission(current_user, session, item_group_id, PermissionLevel.ADMIN)
    
    # Find user by email
    target_user = session.exec(
        select(AppUser).where(AppUser.user_email == request.user_email)
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{request.user_email}' not found"
        )
    
    # Grant permission
    pm = PermissionManager(session)
    pm.grant_permission(
        user_id=target_user.app_user_id,
        resource_type=ResourceType.ITEM_GROUP,
        resource_id=item_group_id,
        permission_level=request.permission_level,
        granted_by=current_user.app_user_id
    )
    session.commit()
    
    return {
        "message": f"Permission '{request.permission_level}' granted to {request.user_email}"
    }


# Warehouse management routes
@router.post("/warehouses/{warehouse_id}/grant", summary="Grant Warehouse Permission")
def grant_warehouse_permission(
    warehouse_id: UUID,
    request: GrantPermissionRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Grant permission on warehouse to user by email. Requires admin permission."""
    
    require_warehouse_permission(current_user, session, warehouse_id, PermissionLevel.ADMIN)
    
    # Find user by email
    target_user = session.exec(
        select(AppUser).where(AppUser.user_email == request.user_email)
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{request.user_email}' not found"
        )
    
    # Grant permission
    pm = PermissionManager(session)
    pm.grant_permission(
        user_id=target_user.app_user_id,
        resource_type=ResourceType.WAREHOUSE,
        resource_id=warehouse_id,
        permission_level=request.permission_level,
        granted_by=current_user.app_user_id
    )
    session.commit()
    
    return {
        "message": f"Permission '{request.permission_level}' granted to {request.user_email}"
    }


@router.get("/warehouses/{warehouse_id}/permissions", response_model=List[PermissionResponse], summary="List Warehouse Permissions")
def list_warehouse_permissions(
    warehouse_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> List[PermissionResponse]:
    """Get all users with permissions for warehouse. Requires admin permission."""
    
    require_warehouse_permission(current_user, session, warehouse_id, PermissionLevel.ADMIN)
    
    pm = PermissionManager(session)
    permissions = pm.get_resource_permissions(ResourceType.WAREHOUSE, warehouse_id)
    
    return [
        PermissionResponse(
            user_id=perm["user_id"],
            user_email=perm["user_email"],
            user_name=perm["user_name"],
            permission_level=perm["permission_level"],
            granted_at=perm["granted_at"].isoformat(),
            expires_at=perm["expires_at"].isoformat() if perm["expires_at"] else None
        )
        for perm in permissions
    ]


@router.delete("/warehouses/{warehouse_id}/permissions/{user_id}", summary="Revoke Warehouse Permission")
def revoke_warehouse_permission(
    warehouse_id: UUID,
    user_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Revoke user's permission for warehouse. Requires admin permission."""
    
    require_warehouse_permission(current_user, session, warehouse_id, PermissionLevel.ADMIN)
    
    pm = PermissionManager(session)
    success = pm.revoke_permission(
        user_id=user_id,
        resource_type=ResourceType.WAREHOUSE,
        resource_id=warehouse_id,
        revoked_by=current_user.app_user_id
    )
    session.commit()
    
    if success:
        return {"message": "Permission revoked successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )


# User permission summary
@router.get("/my-permissions", response_model=List[UserPermissionSummary], summary="Get My Permissions")
def get_my_permissions(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> List[UserPermissionSummary]:
    """Get current user's permissions summary."""
    
    pm = PermissionManager(session)
    permissions = pm.get_user_permissions(current_user.app_user_id)
    
    return [
        UserPermissionSummary(
            resource_type=perm["resource_type"],
            resource_id=perm["resource_id"],
            permission_level=perm["permission_level"],
            granted_at=perm["granted_at"].isoformat(),
            expires_at=perm["expires_at"].isoformat() if perm["expires_at"] else None
        )
        for perm in permissions
    ]