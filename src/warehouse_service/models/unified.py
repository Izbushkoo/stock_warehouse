"""Unified warehouse database models according to the specification."""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func, Column, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, INET, UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel


def uuid_field() -> Field:
    """Generate UUID field with default value."""
    return Field(default_factory=uuid4, primary_key=True, sa_type=PGUUID(as_uuid=True))


def created_at_field() -> Field:
    """Generate created_at timestamp field."""
    return Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


def updated_at_field() -> Field:
    """Generate updated_at timestamp field with auto-update."""
    return Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


# 1. Warehouse Topology Models

class Warehouse(SQLModel, table=True):
    """Warehouse entity representing physical warehouse locations."""
    
    __tablename__ = "warehouse"
    
    warehouse_id: UUID = uuid_field()
    warehouse_code: str = Field(unique=True, index=True)
    warehouse_name: str
    warehouse_address: Optional[str] = None
    time_zone: str = Field(default="Europe/Moscow")
    is_active: bool = Field(default=True)
    item_group_id: UUID = Field(foreign_key="item_group.item_group_id")
    created_by: UUID = Field(foreign_key="app_user.app_user_id")
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    deleted_by: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    



class Zone(SQLModel, table=True):
    """Zone within a warehouse (receiving, storage, picking, etc.)."""
    
    __tablename__ = "zone"
    __table_args__ = (
        CheckConstraint("zone_function IN ('receiving', 'storage', 'picking', 'shipping', 'returns', 'scrap')", name='ck_zone_function'),
    )
    
    zone_id: UUID = uuid_field()
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    zone_name: str
    zone_function: str  # receiving, storage, picking, shipping, returns, scrap
    processing_priority: int = Field(default=100)
    

class BinLocation(SQLModel, table=True):
    """Specific storage bin/location within a zone."""
    
    __tablename__ = "bin_location"
    __table_args__ = (
        CheckConstraint("bin_location_type IN ('pallet', 'shelf', 'flow_rack', 'staging')", name='ck_bin_location_type'),
        UniqueConstraint('warehouse_id', 'bin_location_code', name='uq_bin_location_warehouse_code'),
    )
    
    bin_location_id: UUID = uuid_field()
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    zone_id: UUID = Field(foreign_key="zone.zone_id")
    bin_location_code: str
    bin_location_type: str  # pallet, shelf, flow_rack, staging
    maximum_weight_kilograms: Optional[Decimal] = Field(default=None, decimal_places=3)
    maximum_volume_cubic_meters: Optional[Decimal] = Field(default=None, decimal_places=4)
    is_pick_face: bool = Field(default=False)
    

# 2. Item and Product Models

class ItemGroup(SQLModel, table=True):
    """Group of items with shared handling policies."""
    
    __tablename__ = "item_group"
    
    item_group_id: UUID = uuid_field()
    item_group_code: str = Field(unique=True, index=True)
    item_group_name: str
    item_group_description: Optional[str] = Field(default=None)
    handling_policy: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    is_active: bool = Field(default=True)
    created_by: UUID = Field(foreign_key="app_user.app_user_id")
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    deleted_by: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    

class Item(SQLModel, table=True):
    """Item/Product entity with SKU and characteristics."""
    
    __tablename__ = "item"
    __table_args__ = (
        CheckConstraint("item_status IN ('active', 'archived')", name='ck_item_status'),
    )
    
    item_id: UUID = uuid_field()
    stock_keeping_unit: str = Field(unique=True, index=True)  # SKU
    item_name: str
    unit_of_measure: str = Field(default="pieces")
    barcode_value: Optional[str] = None
    gross_weight_kilograms: Optional[Decimal] = Field(default=None, decimal_places=3)
    volume_cubic_meters: Optional[Decimal] = Field(default=None, decimal_places=4)
    is_lot_tracked: bool = Field(default=False)
    is_serial_number_tracked: bool = Field(default=False)
    item_group_id: UUID = Field(foreign_key="item_group.item_group_id")
    item_status: str = Field(default="active")
    created_by: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    deleted_by: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    

class Lot(SQLModel, table=True):
    """Lot/batch tracking for items."""
    
    __tablename__ = "lot"
    __table_args__ = (
        UniqueConstraint('item_id', 'lot_code', name='uq_lot_item_code'),
    )
    
    lot_id: UUID = uuid_field()
    item_id: UUID = Field(foreign_key="item.item_id")
    lot_code: str
    manufactured_at: Optional[date] = None
    expiration_date: Optional[date] = None
    lot_attributes: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    

class SerialNumber(SQLModel, table=True):
    """Serial number tracking for individual items."""
    
    __tablename__ = "serial_number"
    __table_args__ = (
        CheckConstraint("serial_status IN ('in_stock', 'shipped', 'scrapped')", name='ck_serial_status'),
    )
    
    serial_number_id: UUID = uuid_field()
    item_id: UUID = Field(foreign_key="item.item_id")
    serial_code: str = Field(unique=True, index=True)
    lot_id: Optional[UUID] = Field(default=None, foreign_key="lot.lot_id")
    serial_status: str = Field(default="in_stock")
    

# 3. User and RBAC Models

class AppUser(SQLModel, table=True):
    """Application user with authentication and profile info."""
    
    __tablename__ = "app_user"
    
    app_user_id: UUID = uuid_field()
    user_email: str = Field(unique=True, index=True)
    user_display_name: str
    password_hash: str
    is_active: bool = Field(default=True)
    last_login_at: Optional[datetime] = None
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
    

# Расширяемая система разрешений
class Permission(SQLModel, table=True):
    """Flexible permission system for different resource types."""
    
    __tablename__ = "permission"
    __table_args__ = (
        CheckConstraint("resource_type IN ('item_group', 'warehouse', 'audit', 'marketplace_accounts', 'system')", name='ck_resource_type'),
        CheckConstraint("permission_level IN ('read', 'write', 'admin', 'owner')", name='ck_permission_level'),
        UniqueConstraint('app_user_id', 'resource_type', 'resource_id', name='uq_user_resource_permission'),
    )
    
    permission_id: UUID = uuid_field()
    app_user_id: UUID = Field(foreign_key="app_user.app_user_id")
    resource_type: str  # item_group, warehouse, audit, marketplace_accounts, system
    resource_id: UUID  # ID конкретного ресурса (item_group_id, warehouse_id, etc.)
    permission_level: str  # read, write, admin, owner
    granted_by: UUID = Field(foreign_key="app_user.app_user_id")
    granted_at: datetime = created_at_field()
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)


# WarehouseAccessGrant удален - используем только Permission систему
    

# 4. Stock Movement System (Core)

class StockMovement(SQLModel, table=True):
    """Core stock movement table - source of truth for all inventory changes."""
    
    __tablename__ = "stock_movement"
    __table_args__ = (
        CheckConstraint('moved_quantity != 0', name='ck_moved_quantity_not_zero'),
        CheckConstraint("movement_reason IN ('goods_receipt', 'sales_issue', 'internal_transfer', 'manual_adjustment', 'return_receipt', 'return_scrap', 'inventory_adjustment')", name='ck_movement_reason'),
        Index('ix_stock_movement_occurred_at', 'occurred_at'),
        Index('ix_stock_movement_item_id', 'item_id'),
        Index('ix_stock_movement_warehouse_id', 'warehouse_id'),
        Index('ix_stock_movement_correlation_id', 'correlation_identifier'),
    )
    
    stock_movement_id: UUID = uuid_field()
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    source_bin_location_id: Optional[UUID] = Field(default=None, foreign_key="bin_location.bin_location_id")
    destination_bin_location_id: Optional[UUID] = Field(default=None, foreign_key="bin_location.bin_location_id")
    item_id: UUID = Field(foreign_key="item.item_id")
    lot_id: Optional[UUID] = Field(default=None, foreign_key="lot.lot_id")
    serial_number_id: Optional[UUID] = Field(default=None, foreign_key="serial_number.serial_number_id")
    moved_quantity: Decimal = Field(decimal_places=3)
    unit_of_measure: str
    movement_reason: str
    document_type: Optional[str] = None
    document_identifier: Optional[UUID] = None
    actor_user_id: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    trigger_source: str
    transaction_group: Optional[UUID] = None
    correlation_identifier: Optional[UUID] = None
    notes: Optional[str] = None
    

class StockBalance(SQLModel, table=True):
    """Materialized view of current stock balances."""
    
    __tablename__ = "stock_balance"
    __table_args__ = (
        UniqueConstraint('warehouse_id', 'bin_location_id', 'item_id', 'lot_id', 'serial_number_id', name='uq_stock_balance_unique'),
        Index('ix_stock_balance_warehouse_item', 'warehouse_id', 'item_id'),
        Index('ix_stock_balance_bin_location', 'bin_location_id'),
    )
    
    stock_balance_id: UUID = uuid_field()
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    bin_location_id: UUID = Field(foreign_key="bin_location.bin_location_id")
    item_id: UUID = Field(foreign_key="item.item_id")
    lot_id: Optional[UUID] = Field(default=None, foreign_key="lot.lot_id")
    serial_number_id: Optional[UUID] = Field(default=None, foreign_key="serial_number.serial_number_id")
    quantity_on_hand: Decimal = Field(default=Decimal('0'), decimal_places=3)
    quantity_reserved: Decimal = Field(default=Decimal('0'), decimal_places=3)
    last_movement_at: Optional[datetime] = None
    

# 5. Sales Orders and Reservations

class SalesOrder(SQLModel, table=True):
    """Sales order from marketplace or direct sales."""
    
    __tablename__ = "sales_order"
    __table_args__ = (
        CheckConstraint("sales_order_status IN ('draft', 'allocated', 'shipped', 'closed')", name='ck_sales_order_status'),
    )
    
    sales_order_id: UUID = uuid_field()
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    sales_order_number: str = Field(unique=True, index=True)
    external_sales_channel: Optional[str] = None  # ozon, wildberries, allegro, etc.
    external_order_identifier: Optional[str] = None
    sales_order_status: str = Field(default="draft")
    order_date: datetime
    created_at: datetime = created_at_field()
    created_by_user_id: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    updated_at: datetime = updated_at_field()
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    deleted_by: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    

class SalesOrderLine(SQLModel, table=True):
    """Line item in a sales order."""
    
    __tablename__ = "sales_order_line"
    
    sales_order_line_id: UUID = uuid_field()
    sales_order_id: UUID = Field(foreign_key="sales_order.sales_order_id", ondelete="CASCADE")
    item_id: UUID = Field(foreign_key="item.item_id")
    ordered_quantity: Decimal = Field(decimal_places=3)
    unit_price: Optional[Decimal] = Field(default=None, decimal_places=2)
    allocated_quantity: Decimal = Field(default=Decimal('0'), decimal_places=3)
    shipped_quantity: Decimal = Field(default=Decimal('0'), decimal_places=3)
    

class InventoryReservation(SQLModel, table=True):
    """Inventory reservation for sales orders."""
    
    __tablename__ = "inventory_reservation"
    __table_args__ = (
        CheckConstraint("reservation_status IN ('active', 'released', 'consumed')", name='ck_reservation_status'),
    )
    
    inventory_reservation_id: UUID = uuid_field()
    sales_order_id: UUID = Field(foreign_key="sales_order.sales_order_id")
    sales_order_line_id: UUID = Field(foreign_key="sales_order_line.sales_order_line_id")
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    bin_location_id: UUID = Field(foreign_key="bin_location.bin_location_id")
    item_id: UUID = Field(foreign_key="item.item_id")
    lot_id: Optional[UUID] = Field(default=None, foreign_key="lot.lot_id")
    serial_number_id: Optional[UUID] = Field(default=None, foreign_key="serial_number.serial_number_id")
    reserved_quantity: Decimal = Field(decimal_places=3)
    reservation_status: str = Field(default="active")
    created_at: datetime = created_at_field()
    

# 6. Return Orders

class ReturnOrder(SQLModel, table=True):
    """Return order for returned merchandise."""
    
    __tablename__ = "return_order"
    __table_args__ = (
        CheckConstraint("return_status IN ('received', 'inspected', 'closed')", name='ck_return_status'),
    )
    
    return_order_id: UUID = uuid_field()
    related_sales_order_id: Optional[UUID] = Field(default=None, foreign_key="sales_order.sales_order_id")
    return_reference: Optional[str] = None
    return_reason: Optional[str] = None
    return_status: str = Field(default="received")
    created_at: datetime = created_at_field()
    created_by_user_id: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    updated_at: datetime = updated_at_field()
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    deleted_by: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    

class ReturnOrderLine(SQLModel, table=True):
    """Line item in a return order."""
    
    __tablename__ = "return_order_line"
    __table_args__ = (
        CheckConstraint("inspection_decision IN ('return_to_stock', 'scrap', 'repair')", name='ck_inspection_decision'),
    )
    
    return_order_line_id: UUID = uuid_field()
    return_order_id: UUID = Field(foreign_key="return_order.return_order_id", ondelete="CASCADE")
    item_id: UUID = Field(foreign_key="item.item_id")
    returned_quantity: Decimal = Field(decimal_places=3)
    inspection_decision: Optional[str] = None
    decision_notes: Optional[str] = None
    

# 7. Media and Documents

class MediaAsset(SQLModel, table=True):
    """Immutable media asset storage."""
    
    __tablename__ = "media_asset"
    __table_args__ = (
        CheckConstraint('byte_size >= 0', name='ck_byte_size_positive'),
        CheckConstraint("storage_backend IN ('database', 's3')", name='ck_storage_backend'),
    )
    
    media_asset_id: UUID = uuid_field()
    original_filename: str
    content_sha256: str = Field(unique=True, index=True)
    mime_type: str
    byte_size: int
    storage_backend: str
    storage_bucket: Optional[str] = None
    storage_key: Optional[str] = None
    stored_bytes: Optional[bytes] = None
    is_immutable: bool = Field(default=True)
    worm_retention_until: Optional[datetime] = None
    technical_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    uploaded_at: datetime = created_at_field()
    uploaded_by_user_id: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    

class MediaDerivative(SQLModel, table=True):
    """Generated derivatives of media assets (thumbnails, previews)."""
    
    __tablename__ = "media_derivative"
    __table_args__ = (
        CheckConstraint("storage_backend IN ('database', 's3')", name='ck_derivative_storage_backend'),
        UniqueConstraint('media_asset_id', 'derivative_type', name='uq_media_derivative'),
    )
    
    media_derivative_id: UUID = uuid_field()
    media_asset_id: UUID = Field(foreign_key="media_asset.media_asset_id", ondelete="CASCADE")
    derivative_type: str  # thumbnail_200, preview_800, webp_1200
    mime_type: str
    byte_size: int
    storage_backend: str
    storage_bucket: Optional[str] = None
    storage_key: Optional[str] = None
    stored_bytes: Optional[bytes] = None
    pixel_width: Optional[int] = None
    pixel_height: Optional[int] = None
    generated_at: datetime = created_at_field()
    

class ItemImage(SQLModel, table=True):
    """Images associated with items."""
    
    __tablename__ = "item_image"
    __table_args__ = (
        UniqueConstraint('item_id', 'media_asset_id', name='uq_item_image'),
    )
    
    item_image_id: UUID = uuid_field()
    item_id: UUID = Field(foreign_key="item.item_id", ondelete="CASCADE")
    media_asset_id: UUID = Field(foreign_key="media_asset.media_asset_id")
    is_primary: bool = Field(default=False)
    display_order: int = Field(default=100)
    alt_text: Optional[str] = None
    

class DocumentFile(SQLModel, table=True):
    """Documents attached to business operations."""
    
    __tablename__ = "document_file"
    
    document_file_id: UUID = uuid_field()
    document_type: str  # receipt_file, sales_order, return_order
    document_identifier: UUID
    media_asset_id: UUID = Field(foreign_key="media_asset.media_asset_id")
    document_file_role: str  # receipt_scan, invoice, shipping_label
    uploaded_at: datetime = created_at_field()
    uploaded_by_user_id: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    

class MovementAttachment(SQLModel, table=True):
    """Files attached to specific stock movements."""
    
    __tablename__ = "movement_attachment"
    __table_args__ = (
        UniqueConstraint('stock_movement_id', 'media_asset_id', 'attachment_role', name='uq_movement_attachment'),
    )
    
    movement_attachment_id: UUID = uuid_field()
    stock_movement_id: UUID = Field(foreign_key="stock_movement.stock_movement_id", ondelete="CASCADE")
    media_asset_id: UUID = Field(foreign_key="media_asset.media_asset_id")
    attachment_role: str  # photo_proof, barcode_scan
    

# 8. Analytics

class SalesAnalytics(SQLModel, table=True):
    """Detailed sales analytics for each sale."""
    
    __tablename__ = "sales_analytics"
    __table_args__ = (
        Index('ix_sales_analytics_sale_date', 'sale_date'),
        Index('ix_sales_analytics_marketplace', 'marketplace_channel'),
        Index('ix_sales_analytics_item_id', 'item_id'),
    )
    
    sales_analytics_id: UUID = uuid_field()
    sales_order_id: UUID = Field(foreign_key="sales_order.sales_order_id")
    sales_order_line_id: UUID = Field(foreign_key="sales_order_line.sales_order_line_id")
    item_id: UUID = Field(foreign_key="item.item_id")
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    
    # Core metrics
    quantity_sold: Decimal = Field(decimal_places=3)
    unit_sale_price: Decimal = Field(decimal_places=2)
    unit_cost_price: Optional[Decimal] = Field(default=None, decimal_places=2)
    total_revenue: Decimal = Field(decimal_places=2)
    total_cost: Optional[Decimal] = Field(default=None, decimal_places=2)
    gross_margin: Optional[Decimal] = Field(default=None, decimal_places=2)
    margin_percentage: Optional[Decimal] = Field(default=None, decimal_places=2)
    
    # Context
    marketplace_channel: str
    external_order_id: Optional[str] = None
    sale_date: datetime
    season_quarter: Optional[int] = None  # 1,2,3,4
    day_of_week: Optional[int] = None  # 1-7
    
    # Additional metrics
    days_in_stock: Optional[int] = None
    stock_turnover_rate: Optional[Decimal] = Field(default=None, decimal_places=4)
    
    created_at: datetime = created_at_field()
    

class PurchaseRecommendation(SQLModel, table=True):
    """Purchase recommendations based on sales analytics."""
    
    __tablename__ = "purchase_recommendation"
    __table_args__ = (
        CheckConstraint("sales_velocity_trend IN ('increasing', 'stable', 'decreasing')", name='ck_sales_velocity_trend'),
    )
    
    recommendation_id: UUID = uuid_field()
    item_id: UUID = Field(foreign_key="item.item_id")
    warehouse_id: UUID = Field(foreign_key="warehouse.warehouse_id")
    
    # Current state
    current_stock: Decimal = Field(decimal_places=3)
    reserved_stock: Decimal = Field(decimal_places=3)
    available_stock: Decimal = Field(decimal_places=3)
    
    # Sales analytics
    avg_daily_sales: Optional[Decimal] = Field(default=None, decimal_places=3)
    sales_velocity_trend: Optional[str] = None
    days_of_stock_remaining: Optional[int] = None
    
    # Recommendations
    recommended_order_quantity: Optional[Decimal] = Field(default=None, decimal_places=3)
    recommended_order_date: Optional[date] = None
    priority_score: Optional[Decimal] = Field(default=None, decimal_places=2)  # 0-100
    recommendation_reason: Optional[str] = None
    
    # Seasonality
    seasonal_factor: Optional[Decimal] = Field(default=None, decimal_places=2)
    
    calculated_at: datetime = created_at_field()
    is_active: bool = Field(default=True)


# 9. Audit and Events

class AuditLog(SQLModel, table=True):
    """Complete audit trail of all changes."""
    
    __tablename__ = "audit_log"
    __table_args__ = (
        Index('ix_audit_log_recorded_at', 'recorded_at'),
        Index('ix_audit_log_entity', 'entity_table_name', 'entity_primary_identifier'),
    )
    
    audit_log_id: UUID = uuid_field()
    recorded_at: datetime = created_at_field()
    actor_user_id: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    audited_action: str  # INSERT, UPDATE, DELETE, BUSINESS_EVENT
    entity_table_name: str
    entity_primary_identifier: UUID
    before_state: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    after_state: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    request_ip_address: Optional[str] = Field(default=None, sa_column=Column(INET))
    request_user_agent: Optional[str] = None
    correlation_identifier: Optional[UUID] = None


class DomainEvent(SQLModel, table=True):
    """Business domain events for integration."""
    
    __tablename__ = "domain_event"
    __table_args__ = (
        Index('ix_domain_event_occurred_at', 'occurred_at'),
        Index('ix_domain_event_aggregate', 'aggregate_type', 'aggregate_identifier'),
    )
    
    domain_event_id: UUID = uuid_field()
    occurred_at: datetime = created_at_field()
    event_name: str  # GoodsReceived, SalesOrderShipped, ReturnProcessed
    aggregate_type: str  # sales_order, stock_movement, return_order
    aggregate_identifier: UUID
    event_payload: dict = Field(sa_column=Column(JSONB))
    actor_user_id: Optional[UUID] = Field(default=None, foreign_key="app_user.app_user_id")
    transaction_group: Optional[UUID] = None
    correlation_identifier: Optional[UUID] = None


# Export all models
__all__ = [
    "Warehouse", "Zone", "BinLocation",
    "ItemGroup", "Item", "Lot", "SerialNumber",
    "AppUser", "Permission",
    "StockMovement", "StockBalance",
    "SalesOrder", "SalesOrderLine", "InventoryReservation",
    "ReturnOrder", "ReturnOrderLine",
    "MediaAsset", "MediaDerivative", "ItemImage", "DocumentFile", "MovementAttachment",
    "SalesAnalytics", "PurchaseRecommendation",
    "AuditLog", "DomainEvent"
]