"""Unified RBAC system for warehouse operations."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Set
from uuid import UUID

from sqlmodel import Session, select

from warehouse_service.models.unified import (
    AppUser, WarehouseAccessGrant, Warehouse, ItemGroup, Zone, BinLocation
)


class ScopeType(str, Enum):
    """Types of access control scopes."""
    WAREHOUSE = "warehouse"
    ZONE = "zone"
    BIN_LOCATION = "bin_location"
    ITEM_GROUP = "item_group"


class Permission(str, Enum):
    """Permission types for warehouse operations."""
    READ = "read"
    WRITE = "write"
    APPROVE = "approve"


class WarehouseOperation(str, Enum):
    """Warehouse operations that require permission checks."""
    VIEW_INVENTORY = "view_inventory"
    CREATE_MOVEMENT = "create_movement"
    APPROVE_MOVEMENT = "approve_movement"
    VIEW_SALES_ORDER = "view_sales_order"
    CREATE_SALES_ORDER = "create_sales_order"
    SHIP_SALES_ORDER = "ship_sales_order"
    VIEW_RETURN_ORDER = "view_return_order"
    CREATE_RETURN_ORDER = "create_return_order"
    PROCESS_RETURN = "process_return"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_USERS = "manage_users"
    UPLOAD_MEDIA = "upload_media"
    MANUAL_ADJUSTMENT = "manual_adjustment"


# Operation to permission mapping
OPERATION_PERMISSIONS = {
    WarehouseOperation.VIEW_INVENTORY: Permission.READ,
    WarehouseOperation.CREATE_MOVEMENT: Permission.WRITE,
    WarehouseOperation.APPROVE_MOVEMENT: Permission.APPROVE,
    WarehouseOperation.VIEW_SALES_ORDER: Permission.READ,
    WarehouseOperation.CREATE_SALES_ORDER: Permission.WRITE,
    WarehouseOperation.SHIP_SALES_ORDER: Permission.WRITE,
    WarehouseOperation.VIEW_RETURN_ORDER: Permission.READ,
    WarehouseOperation.CREATE_RETURN_ORDER: Permission.WRITE,
    WarehouseOperation.PROCESS_RETURN: Permission.WRITE,
    WarehouseOperation.VIEW_ANALYTICS: Permission.READ,
    WarehouseOperation.MANAGE_USERS: Permission.APPROVE,
    WarehouseOperation.UPLOAD_MEDIA: Permission.WRITE,
    WarehouseOperation.MANUAL_ADJUSTMENT: Permission.APPROVE,
}


class AccessContext:
    """Context for access control decisions."""
    
    def __init__(
        self,
        warehouse_id: UUID,
        item_group_id: Optional[UUID] = None,
        zone_id: Optional[UUID] = None,
        bin_location_id: Optional[UUID] = None,
    ):
        self.warehouse_id = warehouse_id
        self.item_group_id = item_group_id
        self.zone_id = zone_id
        self.bin_location_id = bin_location_id


class RBACService:
    """Service for role-based access control operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def check_permission(
        self,
        user_id: UUID,
        operation: WarehouseOperation,
        context: AccessContext,
    ) -> bool:
        """Check if user has permission to perform operation in given context."""
        required_permission = OPERATION_PERMISSIONS[operation]
        
        # Get user's access grants for the warehouse
        grants = self._get_user_grants(user_id, context.warehouse_id)
        
        # Check permissions in order of specificity
        # 1. Bin location level (most specific)
        if context.bin_location_id:
            if self._check_bin_location_permission(grants, context.bin_location_id, required_permission):
                return True
        
        # 2. Zone level
        if context.zone_id:
            if self._check_zone_permission(grants, context.zone_id, required_permission):
                return True
        
        # 3. Item group level
        if context.item_group_id:
            if self._check_item_group_permission(grants, context.item_group_id, required_permission):
                return True
        
        # 4. Warehouse level (least specific)
        return self._check_warehouse_permission(grants, context.warehouse_id, required_permission)
    
    def get_accessible_warehouses(self, user_id: UUID) -> List[UUID]:
        """Get list of warehouse IDs user has access to."""
        stmt = select(WarehouseAccessGrant.warehouse_id).where(
            WarehouseAccessGrant.app_user_id == user_id,
            WarehouseAccessGrant.can_read == True
        ).distinct()
        
        result = self.session.exec(stmt)
        return list(result)
    
    def get_accessible_item_groups(self, user_id: UUID, warehouse_id: UUID) -> List[UUID]:
        """Get list of item group IDs user has access to in a warehouse."""
        stmt = select(WarehouseAccessGrant.scope_entity_identifier).where(
            WarehouseAccessGrant.app_user_id == user_id,
            WarehouseAccessGrant.warehouse_id == warehouse_id,
            WarehouseAccessGrant.scope_type == ScopeType.ITEM_GROUP,
            WarehouseAccessGrant.can_read == True,
            WarehouseAccessGrant.scope_entity_identifier.is_not(None)
        )
        
        result = self.session.exec(stmt)
        return list(result)
    
    def grant_warehouse_access(
        self,
        user_id: UUID,
        warehouse_id: UUID,
        can_read: bool = True,
        can_write: bool = False,
        can_approve: bool = False,
    ) -> WarehouseAccessGrant:
        """Grant warehouse-level access to user."""
        grant = WarehouseAccessGrant(
            app_user_id=user_id,
            warehouse_id=warehouse_id,
            scope_type=ScopeType.WAREHOUSE,
            scope_entity_identifier=warehouse_id,
            can_read=can_read,
            can_write=can_write,
            can_approve=can_approve,
        )
        
        self.session.add(grant)
        self.session.commit()
        self.session.refresh(grant)
        return grant
    
    def grant_item_group_access(
        self,
        user_id: UUID,
        warehouse_id: UUID,
        item_group_id: UUID,
        can_read: bool = True,
        can_write: bool = False,
        can_approve: bool = False,
    ) -> WarehouseAccessGrant:
        """Grant item group-level access to user."""
        grant = WarehouseAccessGrant(
            app_user_id=user_id,
            warehouse_id=warehouse_id,
            scope_type=ScopeType.ITEM_GROUP,
            scope_entity_identifier=item_group_id,
            can_read=can_read,
            can_write=can_write,
            can_approve=can_approve,
        )
        
        self.session.add(grant)
        self.session.commit()
        self.session.refresh(grant)
        return grant
    
    def grant_zone_access(
        self,
        user_id: UUID,
        warehouse_id: UUID,
        zone_id: UUID,
        can_read: bool = True,
        can_write: bool = False,
        can_approve: bool = False,
    ) -> WarehouseAccessGrant:
        """Grant zone-level access to user."""
        grant = WarehouseAccessGrant(
            app_user_id=user_id,
            warehouse_id=warehouse_id,
            scope_type=ScopeType.ZONE,
            scope_entity_identifier=zone_id,
            can_read=can_read,
            can_write=can_write,
            can_approve=can_approve,
        )
        
        self.session.add(grant)
        self.session.commit()
        self.session.refresh(grant)
        return grant
    
    def revoke_access(self, user_id: UUID, warehouse_id: UUID, scope_type: ScopeType, scope_entity_id: Optional[UUID] = None):
        """Revoke specific access grant."""
        stmt = select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user_id,
            WarehouseAccessGrant.warehouse_id == warehouse_id,
            WarehouseAccessGrant.scope_type == scope_type,
            WarehouseAccessGrant.scope_entity_identifier == scope_entity_id,
        )
        
        grant = self.session.exec(stmt).first()
        if grant:
            self.session.delete(grant)
            self.session.commit()
    
    def get_user_permissions_summary(self, user_id: UUID) -> dict:
        """Get comprehensive summary of user's permissions."""
        stmt = select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user_id
        )
        
        grants = self.session.exec(stmt).all()
        
        summary = {
            "warehouses": {},
            "total_grants": len(grants),
        }
        
        for grant in grants:
            warehouse_id = str(grant.warehouse_id)
            if warehouse_id not in summary["warehouses"]:
                summary["warehouses"][warehouse_id] = {
                    "warehouse_level": {},
                    "item_groups": {},
                    "zones": {},
                    "bin_locations": {},
                }
            
            permissions = {
                "read": grant.can_read,
                "write": grant.can_write,
                "approve": grant.can_approve,
            }
            
            if grant.scope_type == ScopeType.WAREHOUSE:
                summary["warehouses"][warehouse_id]["warehouse_level"] = permissions
            elif grant.scope_type == ScopeType.ITEM_GROUP:
                summary["warehouses"][warehouse_id]["item_groups"][str(grant.scope_entity_identifier)] = permissions
            elif grant.scope_type == ScopeType.ZONE:
                summary["warehouses"][warehouse_id]["zones"][str(grant.scope_entity_identifier)] = permissions
            elif grant.scope_type == ScopeType.BIN_LOCATION:
                summary["warehouses"][warehouse_id]["bin_locations"][str(grant.scope_entity_identifier)] = permissions
        
        return summary
    
    def _get_user_grants(self, user_id: UUID, warehouse_id: UUID) -> List[WarehouseAccessGrant]:
        """Get all access grants for user in specific warehouse."""
        stmt = select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user_id,
            WarehouseAccessGrant.warehouse_id == warehouse_id,
        )
        
        return list(self.session.exec(stmt))
    
    def _check_warehouse_permission(
        self, 
        grants: List[WarehouseAccessGrant], 
        warehouse_id: UUID, 
        required_permission: Permission
    ) -> bool:
        """Check warehouse-level permission."""
        for grant in grants:
            if (grant.scope_type == ScopeType.WAREHOUSE and 
                grant.scope_entity_identifier == warehouse_id):
                return self._has_permission(grant, required_permission)
        return False
    
    def _check_item_group_permission(
        self, 
        grants: List[WarehouseAccessGrant], 
        item_group_id: UUID, 
        required_permission: Permission
    ) -> bool:
        """Check item group-level permission."""
        for grant in grants:
            if (grant.scope_type == ScopeType.ITEM_GROUP and 
                grant.scope_entity_identifier == item_group_id):
                return self._has_permission(grant, required_permission)
        return False
    
    def _check_zone_permission(
        self, 
        grants: List[WarehouseAccessGrant], 
        zone_id: UUID, 
        required_permission: Permission
    ) -> bool:
        """Check zone-level permission."""
        for grant in grants:
            if (grant.scope_type == ScopeType.ZONE and 
                grant.scope_entity_identifier == zone_id):
                return self._has_permission(grant, required_permission)
        return False
    
    def _check_bin_location_permission(
        self, 
        grants: List[WarehouseAccessGrant], 
        bin_location_id: UUID, 
        required_permission: Permission
    ) -> bool:
        """Check bin location-level permission."""
        for grant in grants:
            if (grant.scope_type == ScopeType.BIN_LOCATION and 
                grant.scope_entity_identifier == bin_location_id):
                return self._has_permission(grant, required_permission)
        return False
    
    def _has_permission(self, grant: WarehouseAccessGrant, required_permission: Permission) -> bool:
        """Check if grant provides required permission."""
        if required_permission == Permission.READ:
            return grant.can_read
        elif required_permission == Permission.WRITE:
            return grant.can_write
        elif required_permission == Permission.APPROVE:
            return grant.can_approve
        return False


class RBACDecorator:
    """Decorator for enforcing RBAC on service methods."""
    
    def __init__(self, operation: WarehouseOperation):
        self.operation = operation
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Extract user_id and context from arguments
            # This would need to be implemented based on your service method signatures
            # For now, this is a placeholder showing the pattern
            user_id = kwargs.get('user_id')
            context = kwargs.get('access_context')
            
            if user_id and context:
                # Get session from service instance (first argument)
                service = args[0]
                rbac = RBACService(service.session)
                
                if not rbac.check_permission(user_id, self.operation, context):
                    raise PermissionError(f"User {user_id} does not have permission for {self.operation}")
            
            return func(*args, **kwargs)
        return wrapper


def require_permission(operation: WarehouseOperation):
    """Decorator factory for requiring specific permissions."""
    return RBACDecorator(operation)


# Utility functions for common permission checks

def can_view_inventory(session: Session, user_id: UUID, warehouse_id: UUID, item_group_id: Optional[UUID] = None) -> bool:
    """Check if user can view inventory in warehouse/item group."""
    rbac = RBACService(session)
    context = AccessContext(warehouse_id=warehouse_id, item_group_id=item_group_id)
    return rbac.check_permission(user_id, WarehouseOperation.VIEW_INVENTORY, context)


def can_create_movement(session: Session, user_id: UUID, warehouse_id: UUID, item_group_id: Optional[UUID] = None) -> bool:
    """Check if user can create stock movements."""
    rbac = RBACService(session)
    context = AccessContext(warehouse_id=warehouse_id, item_group_id=item_group_id)
    return rbac.check_permission(user_id, WarehouseOperation.CREATE_MOVEMENT, context)


def can_approve_movement(session: Session, user_id: UUID, warehouse_id: UUID, item_group_id: Optional[UUID] = None) -> bool:
    """Check if user can approve stock movements."""
    rbac = RBACService(session)
    context = AccessContext(warehouse_id=warehouse_id, item_group_id=item_group_id)
    return rbac.check_permission(user_id, WarehouseOperation.APPROVE_MOVEMENT, context)


def filter_accessible_warehouses(session: Session, user_id: UUID, warehouse_ids: List[UUID]) -> List[UUID]:
    """Filter warehouse list to only include accessible ones."""
    rbac = RBACService(session)
    accessible = rbac.get_accessible_warehouses(user_id)
    return [wh_id for wh_id in warehouse_ids if wh_id in accessible]


def filter_accessible_item_groups(session: Session, user_id: UUID, warehouse_id: UUID, item_group_ids: List[UUID]) -> List[UUID]:
    """Filter item group list to only include accessible ones."""
    rbac = RBACService(session)
    accessible = rbac.get_accessible_item_groups(user_id, warehouse_id)
    return [ig_id for ig_id in item_group_ids if ig_id in accessible]


__all__ = [
    "ScopeType", "Permission", "WarehouseOperation", "AccessContext",
    "RBACService", "require_permission",
    "can_view_inventory", "can_create_movement", "can_approve_movement",
    "filter_accessible_warehouses", "filter_accessible_item_groups"
]