"""RBAC utilities placeholder."""

from __future__ import annotations

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


__all__ = ["PermissionAction", "PermissionScope"]
