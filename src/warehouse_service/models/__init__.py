"""Database models for the unified warehouse service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, UniqueConstraint, func, Column

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel



def created_at_field() -> Field:
    return Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


def updated_at_field() -> Field:
    return Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


class Warehouse(SQLModel, table=True):
    __tablename__ = "warehouses"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    code: str = Field(index=True, unique=True)
    is_primary: bool = Field(default=False)

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    inventories: list["InventoryItem"] = Relationship(back_populates="warehouse")
    permissions: list["WarehousePermission"] = Relationship(back_populates="warehouse")


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    roles: list["UserRole"] = Relationship(back_populates="user")
    warehouse_permissions: list["WarehousePermission"] = Relationship(back_populates="user")
    audits: list["AuditLog"] = Relationship(back_populates="actor")
    owned_inventories: list["Inventory"] = Relationship(back_populates="owner")
    inventory_accesses: list["InventoryAccess"] = Relationship(back_populates="user")

    @property
    def accessible_inventories(self) -> list["Inventory"]:
        return [access.inventory for access in self.inventory_accesses]


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: str | None = None

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    permissions: list["RolePermission"] = Relationship(back_populates="role")
    users: list["UserRole"] = Relationship(back_populates="role")


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("scope", "action", name="uq_permission_scope_action"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scope: str = Field(index=True)
    action: str = Field(index=True)
    description: str | None = None

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    roles: list["RolePermission"] = Relationship(back_populates="permission")


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    role_id: int = Field(foreign_key="roles.id")

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    user: User = Relationship(back_populates="roles")
    role: Role = Relationship(back_populates="users")


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id")
    permission_id: int = Field(foreign_key="permissions.id")

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    role: Role = Relationship(back_populates="permissions")
    permission: Permission = Relationship(back_populates="roles")


class WarehousePermission(SQLModel, table=True):
    __tablename__ = "warehouse_permissions"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "user_id", "permission_id", name="uq_warehouse_permission"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(foreign_key="warehouses.id")
    user_id: int = Field(foreign_key="users.id")
    permission_id: int = Field(foreign_key="permissions.id")

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    warehouse: Warehouse = Relationship(back_populates="permissions")
    user: User = Relationship(back_populates="warehouse_permissions")
    permission: Permission = Relationship()


class InventoryMembership(SQLModel, table=True):
    __tablename__ = "inventory_memberships"

    inventory_id: Optional[int] = Field(
        default=None,
        foreign_key="inventories.id",
        primary_key=True,
    )
    inventory_item_id: Optional[int] = Field(
        default=None,
        foreign_key="inventory_items.id",
        primary_key=True,
    )


class Inventory(SQLModel, table=True):
    __tablename__ = "inventories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    owner_id: int = Field(foreign_key="users.id")
    description: str | None = None

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    owner: User = Relationship(back_populates="owned_inventories")
    items: list["InventoryItem"] = Relationship(
        back_populates="inventories",
        link_model=InventoryMembership,
    )
    accesses: list["InventoryAccess"] = Relationship(back_populates="inventory")

    @property
    def shared_with(self) -> list[User]:
        return [access.user for access in self.accesses]


class InventoryAccess(SQLModel, table=True):
    __tablename__ = "inventory_accesses"
    __table_args__ = (
        UniqueConstraint("inventory_id", "user_id", name="uq_inventory_access"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_id: int = Field(foreign_key="inventories.id")
    user_id: int = Field(foreign_key="users.id")
    granted_by_id: int | None = Field(default=None, foreign_key="users.id")

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    inventory: Inventory = Relationship(back_populates="accesses")
    user: User = Relationship(back_populates="inventory_accesses")
    granted_by: Optional[User] = Relationship()


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True)
    name: str
    description: str | None = None

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    inventories: list["InventoryItem"] = Relationship(back_populates="product")
    audits: list["AuditLog"] = Relationship(back_populates="product")


class InventoryItem(SQLModel, table=True):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_warehouse_product"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(foreign_key="warehouses.id")
    product_id: int = Field(foreign_key="products.id")
    quantity: int = Field(default=0)
    reserved: int = Field(default=0)

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    warehouse: Warehouse = Relationship(back_populates="inventories")
    product: Product = Relationship(back_populates="inventories")
    audits: list["AuditLog"] = Relationship(back_populates="inventory_item")
    inventories: list["Inventory"] = Relationship(
        back_populates="items",
        link_model=InventoryMembership,
    )


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: int | None = Field(default=None, foreign_key="users.id")
    product_id: int | None = Field(default=None, foreign_key="products.id")
    inventory_item_id: int | None = Field(default=None, foreign_key="inventory_items.id")
    warehouse_id: int | None = Field(default=None, foreign_key="warehouses.id")
    action: str
    payload: dict | None = Field(default=None, sa_column=Column(JSONB))
    note: str | None = None

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    actor: Optional[User] = Relationship(back_populates="audits")
    product: Optional[Product] = Relationship(back_populates="audits")
    inventory_item: Optional[InventoryItem] = Relationship(back_populates="audits")
    warehouse: Optional[Warehouse] = Relationship()


metadata = SQLModel.metadata

__all__ = [
    "AuditLog",
    "Inventory",
    "InventoryAccess",
    "InventoryItem",
    "InventoryMembership",
    "Permission",
    "Product",
    "Role",
    "RolePermission",
    "User",
    "UserRole",
    "Warehouse",
    "WarehousePermission",
    "metadata",
]
