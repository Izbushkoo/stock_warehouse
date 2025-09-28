"""RBAC utilities for unified warehouse system."""

from __future__ import annotations

# Import unified RBAC system
from warehouse_service.rbac.unified import *

# Legacy enums for backward compatibility
from enum import Enum

class PermissionAction(str, Enum):
    READ = "read"
    WRITE = "write"
    MANAGE = "manage"

class PermissionScope(str, Enum):
    PRODUCT = "product"
    WAREHOUSE = "warehouse"
    INVENTORY = "inventory"
    USER = "user"

__all__ = [
    # New unified RBAC
    "ScopeType", "Permission", "WarehouseOperation", "AccessContext",
    "RBACService", "require_permission",
    "can_view_inventory", "can_create_movement", "can_approve_movement",
    "filter_accessible_warehouses", "filter_accessible_item_groups",
    
    # Legacy compatibility
    "PermissionAction", "PermissionScope"
]
