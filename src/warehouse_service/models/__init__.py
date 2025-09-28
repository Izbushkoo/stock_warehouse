"""Database models for the unified warehouse service."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


class TimestampMixin(SQLModel, table=False):
    """Common timestamp columns."""

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


class Warehouse(TimestampMixin, table=True):
    __tablename__ = "warehouses"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    code: str = Field(index=True, unique=True)
    is_primary: bool = Field(default=False)

    inventories: list["InventoryItem"] = Relationship(back_populates="warehouse")
    permissions: list["WarehousePermission"] = Relationship(back_populates="warehouse")


class User(TimestampMixin, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)

    roles: list["UserRole"] = Relationship(back_populates="user")
    warehouse_permissions: list["WarehousePermission"] = Relationship(back_populates="user")
    audits: list["AuditLog"] = Relationship(back_populates="actor")


class Role(TimestampMixin, table=True):
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: str | None = None

    permissions: list["RolePermission"] = Relationship(back_populates="role")
    users: list["UserRole"] = Relationship(back_populates="role")


class Permission(TimestampMixin, table=True):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("scope", "action", name="uq_permission_scope_action"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scope: str = Field(index=True)
    action: str = Field(index=True)
    description: str | None = None

    roles: list["RolePermission"] = Relationship(back_populates="permission")


class UserRole(TimestampMixin, table=True):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    role_id: int = Field(foreign_key="roles.id")

    user: User = Relationship(back_populates="roles")
    role: Role = Relationship(back_populates="users")


class RolePermission(TimestampMixin, table=True):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id")
    permission_id: int = Field(foreign_key="permissions.id")

    role: Role = Relationship(back_populates="permissions")
    permission: Permission = Relationship(back_populates="roles")


class WarehousePermission(TimestampMixin, table=True):
    __tablename__ = "warehouse_permissions"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "user_id", "permission_id", name="uq_warehouse_permission"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(foreign_key="warehouses.id")
    user_id: int = Field(foreign_key="users.id")
    permission_id: int = Field(foreign_key="permissions.id")

    warehouse: Warehouse = Relationship(back_populates="permissions")
    user: User = Relationship(back_populates="warehouse_permissions")
    permission: Permission = Relationship()


class Product(TimestampMixin, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True)
    name: str
    description: str | None = None

    inventories: list["InventoryItem"] = Relationship(back_populates="product")
    audits: list["AuditLog"] = Relationship(back_populates="product")


class InventoryItem(TimestampMixin, table=True):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_warehouse_product"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(foreign_key="warehouses.id")
    product_id: int = Field(foreign_key="products.id")
    quantity: int = Field(default=0)
    reserved: int = Field(default=0)

    warehouse: Warehouse = Relationship(back_populates="inventories")
    product: Product = Relationship(back_populates="inventories")
    audits: list["AuditLog"] = Relationship(back_populates="inventory_item")


class AuditLog(TimestampMixin, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: int | None = Field(default=None, foreign_key="users.id")
    product_id: int | None = Field(default=None, foreign_key="products.id")
    inventory_item_id: int | None = Field(default=None, foreign_key="inventory_items.id")
    warehouse_id: int | None = Field(default=None, foreign_key="warehouses.id")
    action: str
    payload: dict | None = Field(default=None, sa_column=Column(JSONB))
    note: str | None = None

    actor: Optional[User] = Relationship(back_populates="audits")
    product: Optional[Product] = Relationship(back_populates="audits")
    inventory_item: Optional[InventoryItem] = Relationship(back_populates="audits")
    warehouse: Optional[Warehouse] = Relationship()


metadata = SQLModel.metadata

__all__ = [
    "AuditLog",
    "InventoryItem",
    "Permission",
    "Product",
    "Role",
    "RolePermission",
    "TimestampMixin",
    "User",
    "UserRole",
    "Warehouse",
    "WarehousePermission",
    "metadata",
]
