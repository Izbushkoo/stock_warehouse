"""Unified flexible permission system for warehouse operations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Set
from uuid import UUID

from sqlmodel import Session, select

from warehouse_service.models.unified import AppUser, Permission, ItemGroup, Warehouse


class ResourceType(str, Enum):
    """Available resource types in the system."""
    ITEM_GROUP = "item_group"    # Каталог товаров
    WAREHOUSE = "warehouse"      # Склад
    SYSTEM = "system"           # Системные разрешения


class PermissionLevel(str, Enum):
    """Permission levels from lowest to highest."""
    READ = "read"          # Просмотр ресурса
    WRITE = "write"        # Изменение ресурса (добавление/списание товаров)
    ADMIN = "admin"        # Управление ресурсом + выдача разрешений
    OWNER = "owner"        # Полный контроль + передача владения


class PermissionManager:
    """Centralized permission management with catalog-warehouse hierarchy."""
    
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
        
        accessible_warehouse_ids = self.get_accessible_warehouse_ids(user_id, item_group_id)
        
        if not accessible_warehouse_ids:
            return []
        
        query = select(Warehouse).where(Warehouse.warehouse_id.in_(accessible_warehouse_ids))
        if item_group_id:
            query = query.where(Warehouse.item_group_id == item_group_id)
            
        return list(self.session.exec(query).all())
    
    def get_accessible_warehouse_ids(self, user_id: UUID, item_group_id: Optional[UUID] = None) -> Set[UUID]:
        """Get set of warehouse IDs user has access to (READ or higher)."""
        
        if self.is_system_admin(user_id):
            query = select(Warehouse.warehouse_id)
            if item_group_id:
                query = query.where(Warehouse.item_group_id == item_group_id)
            return set(self.session.exec(query).all())
        
        accessible_ids = set()
        
        # Get warehouses from direct warehouse permissions
        warehouse_permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == ResourceType.WAREHOUSE.value,
                Permission.is_active.is_(True)
            )
        ).all()
        
        for perm in warehouse_permissions:
            if not perm.expires_at or perm.expires_at > datetime.utcnow():
                accessible_ids.add(perm.resource_id)
        
        # Get warehouses from item group permissions
        item_group_permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == ResourceType.ITEM_GROUP.value,
                Permission.is_active.is_(True)
            )
        ).all()
        
        for perm in item_group_permissions:
            if not perm.expires_at or perm.expires_at > datetime.utcnow():
                # Get all warehouses in this item group
                warehouses = self.session.exec(
                    select(Warehouse.warehouse_id).where(Warehouse.item_group_id == perm.resource_id)
                ).all()
                accessible_ids.update(warehouses)
        
        # Filter by item_group_id if specified
        if item_group_id and accessible_ids:
            warehouses_in_group = set(self.session.exec(
                select(Warehouse.warehouse_id).where(
                    Warehouse.item_group_id == item_group_id,
                    Warehouse.warehouse_id.in_(accessible_ids)
                )
            ).all())
            accessible_ids = accessible_ids.intersection(warehouses_in_group)
        
        return accessible_ids
    
    def get_writable_warehouse_ids(self, user_id: UUID, item_group_id: Optional[UUID] = None) -> Set[UUID]:
        """Get set of warehouse IDs user can write to (WRITE or higher)."""
        
        if self.is_system_admin(user_id):
            query = select(Warehouse.warehouse_id)
            if item_group_id:
                query = query.where(Warehouse.item_group_id == item_group_id)
            return set(self.session.exec(query).all())
        
        writable_ids = set()
        
        # Get warehouses from direct warehouse permissions (WRITE+)
        warehouse_permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == ResourceType.WAREHOUSE.value,
                Permission.permission_level.in_([
                    PermissionLevel.WRITE.value,
                    PermissionLevel.ADMIN.value,
                    PermissionLevel.OWNER.value
                ]),
                Permission.is_active.is_(True)
            )
        ).all()
        
        for perm in warehouse_permissions:
            if not perm.expires_at or perm.expires_at > datetime.utcnow():
                writable_ids.add(perm.resource_id)
        
        # Get warehouses from item group permissions (WRITE+)
        item_group_permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.resource_type == ResourceType.ITEM_GROUP.value,
                Permission.permission_level.in_([
                    PermissionLevel.WRITE.value,
                    PermissionLevel.ADMIN.value,
                    PermissionLevel.OWNER.value
                ]),
                Permission.is_active.is_(True)
            )
        ).all()
        
        for perm in item_group_permissions:
            if not perm.expires_at or perm.expires_at > datetime.utcnow():
                # Get all warehouses in this item group
                warehouses = self.session.exec(
                    select(Warehouse.warehouse_id).where(Warehouse.item_group_id == perm.resource_id)
                ).all()
                writable_ids.update(warehouses)
        
        # Filter by item_group_id if specified
        if item_group_id and writable_ids:
            warehouses_in_group = set(self.session.exec(
                select(Warehouse.warehouse_id).where(
                    Warehouse.item_group_id == item_group_id,
                    Warehouse.warehouse_id.in_(writable_ids)
                )
            ).all())
            writable_ids = writable_ids.intersection(warehouses_in_group)
        
        return writable_ids
    
    def can_read_warehouse(self, user_id: UUID, warehouse_id: UUID) -> bool:
        """Check if user can read warehouse data (view inventory)."""
        return self.has_warehouse_permission(user_id, warehouse_id, PermissionLevel.READ)
    
    def can_write_warehouse(self, user_id: UUID, warehouse_id: UUID) -> bool:
        """Check if user can write to warehouse (add/remove inventory)."""
        return self.has_warehouse_permission(user_id, warehouse_id, PermissionLevel.WRITE)
    
    def can_admin_warehouse(self, user_id: UUID, warehouse_id: UUID) -> bool:
        """Check if user can admin warehouse (manage settings, permissions)."""
        return self.has_warehouse_permission(user_id, warehouse_id, PermissionLevel.ADMIN)
    
    def has_warehouse_permission(self, user_id: UUID, warehouse_id: UUID, required_level: PermissionLevel) -> bool:
        """Check if user has required permission level for warehouse (with item group inheritance)."""
        
        if self.is_system_admin(user_id):
            return True
        
        # Check direct warehouse permission
        if self.has_permission(user_id, ResourceType.WAREHOUSE, warehouse_id, required_level):
            return True
        
        # Check inherited permission from item group
        warehouse = self.session.get(Warehouse, warehouse_id)
        if warehouse and warehouse.item_group_id:
            return self.has_permission(user_id, ResourceType.ITEM_GROUP, warehouse.item_group_id, required_level)
        
        return False
    
    def get_user_warehouse_permissions(self, user_id: UUID) -> Dict[str, Dict[str, Any]]:
        """Get detailed warehouse permissions for user with inheritance info."""
        
        if self.is_system_admin(user_id):
            # System admin has access to all warehouses
            all_warehouses = self.session.exec(select(Warehouse)).all()
            result = {}
            for warehouse in all_warehouses:
                result[str(warehouse.warehouse_id)] = {
                    "warehouse_id": str(warehouse.warehouse_id),
                    "warehouse_name": warehouse.warehouse_name,
                    "item_group_id": str(warehouse.item_group_id),
                    "permissions": {
                        "read": True,
                        "write": True,
                        "admin": True
                    },
                    "source": "system_admin"
                }
            return result
        
        result = {}
        
        # Get all user permissions
        permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_id,
                Permission.is_active.is_(True)
            )
        ).all()
        
        # Process direct warehouse permissions
        for perm in permissions:
            if (perm.resource_type == ResourceType.WAREHOUSE.value and 
                (not perm.expires_at or perm.expires_at > datetime.utcnow())):
                
                warehouse = self.session.get(Warehouse, perm.resource_id)
                if warehouse:
                    warehouse_id = str(warehouse.warehouse_id)
                    user_level = PermissionLevel(perm.permission_level)
                    
                    result[warehouse_id] = {
                        "warehouse_id": warehouse_id,
                        "warehouse_name": warehouse.warehouse_name,
                        "item_group_id": str(warehouse.item_group_id),
                        "permissions": {
                            "read": self._permission_hierarchy_check(user_level, PermissionLevel.READ),
                            "write": self._permission_hierarchy_check(user_level, PermissionLevel.WRITE),
                            "admin": self._permission_hierarchy_check(user_level, PermissionLevel.ADMIN)
                        },
                        "source": "direct_warehouse",
                        "permission_level": perm.permission_level
                    }
        
        # Process item group permissions (inherited by warehouses)
        for perm in permissions:
            if (perm.resource_type == ResourceType.ITEM_GROUP.value and 
                (not perm.expires_at or perm.expires_at > datetime.utcnow())):
                
                # Get all warehouses in this item group
                warehouses = self.session.exec(
                    select(Warehouse).where(Warehouse.item_group_id == perm.resource_id)
                ).all()
                
                user_level = PermissionLevel(perm.permission_level)
                
                for warehouse in warehouses:
                    warehouse_id = str(warehouse.warehouse_id)
                    
                    # Only add if not already present with direct permission
                    if warehouse_id not in result:
                        result[warehouse_id] = {
                            "warehouse_id": warehouse_id,
                            "warehouse_name": warehouse.warehouse_name,
                            "item_group_id": str(warehouse.item_group_id),
                            "permissions": {
                                "read": self._permission_hierarchy_check(user_level, PermissionLevel.READ),
                                "write": self._permission_hierarchy_check(user_level, PermissionLevel.WRITE),
                                "admin": self._permission_hierarchy_check(user_level, PermissionLevel.ADMIN)
                            },
                            "source": "inherited_from_item_group",
                            "permission_level": perm.permission_level
                        }
        
        return result
    
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
    """Raise exception if user doesn't have warehouse permission (with item group inheritance)."""
    from fastapi import HTTPException, status
    
    pm = PermissionManager(session)
    if not pm.has_warehouse_permission(user.app_user_id, warehouse_id, level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for warehouse {warehouse_id}"
        )


def require_warehouse_read(user: AppUser, session: Session, warehouse_id: UUID) -> None:
    """Raise exception if user can't read warehouse."""
    require_warehouse_permission(user, session, warehouse_id, PermissionLevel.READ)


def require_warehouse_write(user: AppUser, session: Session, warehouse_id: UUID) -> None:
    """Raise exception if user can't write to warehouse."""
    require_warehouse_permission(user, session, warehouse_id, PermissionLevel.WRITE)


def require_warehouse_admin(user: AppUser, session: Session, warehouse_id: UUID) -> None:
    """Raise exception if user can't admin warehouse."""
    require_warehouse_permission(user, session, warehouse_id, PermissionLevel.ADMIN)