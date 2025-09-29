"""New flexible permission system for all resource types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlmodel import Session, select

from warehouse_service.models.unified import AppUser, Permission, ItemGroup, Warehouse


class ResourceType(str, Enum):
    """Available resource types in the system."""
    ITEM_GROUP = "item_group"
    WAREHOUSE = "warehouse"
    AUDIT = "audit"
    MARKETPLACE_ACCOUNTS = "marketplace_accounts"
    SYSTEM = "system"


class PermissionLevel(str, Enum):
    """Permission levels from lowest to highest."""
    READ = "read"          # Can view resource
    WRITE = "write"        # Can modify resource
    ADMIN = "admin"        # Can manage resource + grant permissions
    OWNER = "owner"        # Full control + can transfer ownership


class PermissionManager:
    """Centralized permission management."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def grant_permission(
        self,
        user_id: UUID,
        resource_type: ResourceType,
        resource_id: UUID,
        permission_level: PermissionLevel,
        granted_by: UUID,
        expires_at: Optional[datetime] = None
    ) -> Permission:
        """Grant permission to user for specific resource."""
        
        # Check if granter has admin+ rights
        if not self.has_permission(granted_by, resource_type, resource_id, PermissionLevel.ADMIN):
            raise ValueError("Insufficient permissions to grant access")
        
        # Remove existing permission if any
        existing = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == resource_type.value,
                Permission.resource_id == resource_id
            )
        ).first()
        
        if existing:
            existing.permission_level = permission_level.value
            existing.granted_by = granted_by
            existing.granted_at = datetime.utcnow()
            existing.expires_at = expires_at
            existing.is_active = True
            self.session.add(existing)
            return existing
        
        # Create new permission
        permission = Permission(
            app_user_id=user_id,
            resource_type=resource_type.value,
            resource_id=resource_id,
            permission_level=permission_level.value,
            granted_by=granted_by,
            expires_at=expires_at
        )
        
        self.session.add(permission)
        return permission
    
    def revoke_permission(
        self,
        user_id: UUID,
        resource_type: ResourceType,
        resource_id: UUID,
        revoked_by: UUID
    ) -> bool:
        """Revoke user's permission for resource."""
        
        # Check if revoker has admin+ rights
        if not self.has_permission(revoked_by, resource_type, resource_id, PermissionLevel.ADMIN):
            raise ValueError("Insufficient permissions to revoke access")
        
        permission = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == resource_type.value,
                Permission.resource_id == resource_id,
                Permission.is_active.is_(True)
            )
        ).first()
        
        if permission:
            permission.is_active = False
            self.session.add(permission)
            return True
        
        return False
    
    def has_permission(
        self,
        user_id: UUID,
        resource_type: ResourceType,
        resource_id: UUID,
        required_level: PermissionLevel
    ) -> bool:
        """Check if user has required permission level for resource."""
        
        # System admins have all permissions
        if self.is_system_admin(user_id):
            return True
        
        permission = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == resource_type.value,
                Permission.resource_id == resource_id,
                Permission.is_active.is_(True)
            )
        ).first()
        
        if not permission:
            return False
        
        # Check if permission is expired
        if permission.expires_at and permission.expires_at < datetime.utcnow():
            return False
        
        # Check permission hierarchy
        user_level = PermissionLevel(permission.permission_level)
        return self._permission_hierarchy_check(user_level, required_level)
    
    def get_user_permissions(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all active permissions for user."""
        
        permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.is_active.is_(True)
            )
        ).all()
        
        result = []
        for perm in permissions:
            # Skip expired permissions
            if perm.expires_at and perm.expires_at < datetime.utcnow():
                continue
                
            result.append({
                "resource_type": perm.resource_type,
                "resource_id": str(perm.resource_id),
                "permission_level": perm.permission_level,
                "granted_at": perm.granted_at,
                "expires_at": perm.expires_at
            })
        
        return result
    
    def get_resource_permissions(
        self, 
        resource_type: ResourceType, 
        resource_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all users with permissions for specific resource."""
        
        permissions = self.session.exec(
            select(Permission, AppUser).join(AppUser).where(
                Permission.resource_type == resource_type.value,
                Permission.resource_id == resource_id,
                Permission.is_active.is_(True)
            )
        ).all()
        
        result = []
        for perm, user in permissions:
            # Skip expired permissions
            if perm.expires_at and perm.expires_at < datetime.utcnow():
                continue
                
            result.append({
                "user_id": str(user.app_user_id),
                "user_email": user.user_email,
                "user_name": user.user_display_name,
                "permission_level": perm.permission_level,
                "granted_at": perm.granted_at,
                "expires_at": perm.expires_at
            })
        
        return result
    
    def is_system_admin(self, user_id: UUID) -> bool:
        """Check if user is system administrator."""
        
        permission = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.permission_level.in_([PermissionLevel.ADMIN.value, PermissionLevel.OWNER.value]),
                Permission.is_active.is_(True)
            )
        ).first()
        
        return permission is not None
    
    def can_create_item_group(self, user_id: UUID) -> bool:
        """Check if user can create item groups (only system admins)."""
        return self.is_system_admin(user_id)
    
    def can_create_warehouse(self, user_id: UUID, item_group_id: UUID) -> bool:
        """Check if user can create warehouses in item group."""
        return (
            self.is_system_admin(user_id) or
            self.has_permission(user_id, ResourceType.ITEM_GROUP, item_group_id, PermissionLevel.WRITE)
        )
    
    def can_manage_warehouse_permissions(self, user_id: UUID, warehouse_id: UUID) -> bool:
        """Check if user can manage permissions for warehouse."""
        return (
            self.is_system_admin(user_id) or
            self.has_permission(user_id, ResourceType.WAREHOUSE, warehouse_id, PermissionLevel.ADMIN)
        )
    
    def get_user_item_groups(self, user_id: UUID) -> List[ItemGroup]:
        """Get all item groups user has access to."""
        
        if self.is_system_admin(user_id):
            return list(self.session.exec(select(ItemGroup)).all())
        
        # Get item groups where user has permissions
        permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == ResourceType.ITEM_GROUP.value,
                Permission.is_active.is_(True)
            )
        ).all()
        
        item_group_ids = [perm.resource_id for perm in permissions 
                         if not perm.expires_at or perm.expires_at > datetime.utcnow()]
        
        if not item_group_ids:
            return []
        
        return list(self.session.exec(
            select(ItemGroup).where(ItemGroup.item_group_id.in_(item_group_ids))
        ).all())
    
    def get_user_warehouses(self, user_id: UUID, item_group_id: Optional[UUID] = None) -> List[Warehouse]:
        """Get all warehouses user has access to, optionally filtered by item group."""
        
        if self.is_system_admin(user_id):
            query = select(Warehouse)
            if item_group_id:
                query = query.where(Warehouse.item_group_id == item_group_id)
            return list(self.session.exec(query).all())
        
        # Get warehouses where user has direct permissions
        warehouse_permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == ResourceType.WAREHOUSE.value,
                Permission.is_active.is_(True)
            )
        ).all()
        
        warehouse_ids = [perm.resource_id for perm in warehouse_permissions 
                        if not perm.expires_at or perm.expires_at > datetime.utcnow()]
        
        # Also get warehouses from item groups user has access to
        if item_group_id:
            if self.has_permission(user_id, ResourceType.ITEM_GROUP, item_group_id, PermissionLevel.READ):
                item_group_warehouses = self.session.exec(
                    select(Warehouse).where(Warehouse.item_group_id == item_group_id)
                ).all()
                warehouse_ids.extend([w.warehouse_id for w in item_group_warehouses])
        
        if not warehouse_ids:
            return []
        
        return list(self.session.exec(
            select(Warehouse).where(Warehouse.warehouse_id.in_(warehouse_ids))
        ).all())
    
    def _permission_hierarchy_check(self, user_level: PermissionLevel, required_level: PermissionLevel) -> bool:
        """Check if user permission level satisfies required level."""
        
        hierarchy = {
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.ADMIN: 3,
            PermissionLevel.OWNER: 4
        }
        
        return hierarchy[user_level] >= hierarchy[required_level]


# Convenience functions for FastAPI dependencies
def require_system_admin(user: AppUser, session: Session) -> None:
    """Raise exception if user is not system admin."""
    from fastapi import HTTPException, status
    
    pm = PermissionManager(session)
    if not pm.is_system_admin(user.app_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System administrator privileges required"
        )


def require_item_group_permission(
    user: AppUser, 
    session: Session, 
    item_group_id: UUID, 
    level: PermissionLevel = PermissionLevel.READ
) -> None:
    """Raise exception if user doesn't have item group permission."""
    from fastapi import HTTPException, status
    
    pm = PermissionManager(session)
    if not pm.has_permission(user.app_user_id, ResourceType.ITEM_GROUP, item_group_id, level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for item group {item_group_id}"
        )


def require_warehouse_permission(
    user: AppUser, 
    session: Session, 
    warehouse_id: UUID, 
    level: PermissionLevel = PermissionLevel.READ
) -> None:
    """Raise exception if user doesn't have warehouse permission."""
    from fastapi import HTTPException, status
    
    pm = PermissionManager(session)
    if not pm.has_permission(user.app_user_id, ResourceType.WAREHOUSE, warehouse_id, level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for warehouse {warehouse_id}"
        )