"""Database models for the warehouse service."""

from __future__ import annotations

from sqlmodel import SQLModel

# Import unified models without relationships
from warehouse_service.models.unified import *

# Keep metadata for Alembic
metadata = SQLModel.metadata

__all__ = [
    # Core warehouse models
    "Warehouse", "Zone", "BinLocation",
    "ItemGroup", "Item",
    "AppUser", "WarehouseAccessGrant",
    "StockMovement", "StockBalance",
    "SalesOrder",
    "metadata",
]
