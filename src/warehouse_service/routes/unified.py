"""API routes for unified warehouse system."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from warehouse_service.db import session_scope
from warehouse_service.models.unified import (
    Warehouse, Item, StockBalance, StockMovement, SalesOrder, AppUser
)
from warehouse_service.services import StockService, SalesService, MediaService, AnalyticsService

from warehouse_service.auth.dependencies import get_current_user, get_session

router = APIRouter(prefix="/api/v1", tags=["unified-warehouse"])


# Pydantic models for API
class CreateStockMovementRequest(BaseModel):
    warehouse_id: UUID
    item_id: UUID
    moved_quantity: Decimal
    movement_reason: str
    source_bin_location_id: Optional[UUID] = None
    destination_bin_location_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    serial_number_id: Optional[UUID] = None
    notes: Optional[str] = None


class CreateSalesOrderRequest(BaseModel):
    warehouse_id: UUID
    sales_order_number: str
    external_sales_channel: Optional[str] = None
    external_order_identifier: Optional[str] = None
    line_items: List[dict]


class StockBalanceResponse(BaseModel):
    stock_balance_id: UUID
    warehouse_id: UUID
    bin_location_id: UUID
    item_id: UUID
    lot_id: Optional[UUID]
    serial_number_id: Optional[UUID]
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    last_movement_at: Optional[datetime]


class StockMovementResponse(BaseModel):
    stock_movement_id: UUID
    occurred_at: datetime
    warehouse_id: UUID
    source_bin_location_id: Optional[UUID]
    destination_bin_location_id: Optional[UUID]
    item_id: UUID
    moved_quantity: Decimal
    movement_reason: str
    trigger_source: str
    notes: Optional[str]


# Warehouse endpoints
@router.get("/warehouses", response_model=List[dict])
async def list_warehouses(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List all warehouses accessible to user."""
    from warehouse_service.rbac.unified import RBACService
    rbac = RBACService(session)
    accessible_warehouse_ids = rbac.get_accessible_warehouses(current_user.app_user_id)
    
    warehouses = []
    for warehouse_id in accessible_warehouse_ids:
        warehouse = session.get(Warehouse, warehouse_id)
        if warehouse:
            warehouses.append({
                "warehouse_id": str(warehouse.warehouse_id),
                "warehouse_code": warehouse.warehouse_code,
                "warehouse_name": warehouse.warehouse_name,
                "is_active": warehouse.is_active,
            })
    
    return warehouses


@router.get("/warehouses/{warehouse_id}/stock-balance", response_model=List[StockBalanceResponse])
async def get_stock_balance(
    warehouse_id: UUID,
    item_id: Optional[UUID] = None,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get current stock balances for warehouse."""
    stock_service = StockService(session)
    
    balances = stock_service.get_stock_balance(
        warehouse_id=warehouse_id,
        item_id=item_id,
        user_id=current_user.app_user_id
    )
    
    return [
        StockBalanceResponse(
            stock_balance_id=balance.stock_balance_id,
            warehouse_id=balance.warehouse_id,
            bin_location_id=balance.bin_location_id,
            item_id=balance.item_id,
            lot_id=balance.lot_id,
            serial_number_id=balance.serial_number_id,
            quantity_on_hand=balance.quantity_on_hand,
            quantity_reserved=balance.quantity_reserved,
            last_movement_at=balance.last_movement_at,
        )
        for balance in balances
    ]


@router.post("/stock-movements", response_model=StockMovementResponse)
async def create_stock_movement(
    request: CreateStockMovementRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new stock movement."""
    stock_service = StockService(session)
    
    try:
        movement = stock_service.create_stock_movement(
            warehouse_id=request.warehouse_id,
            item_id=request.item_id,
            moved_quantity=request.moved_quantity,
            movement_reason=request.movement_reason,
            actor_user_id=current_user.app_user_id,
            trigger_source=f"api:user:{current_user.app_user_id}",
            source_bin_location_id=request.source_bin_location_id,
            destination_bin_location_id=request.destination_bin_location_id,
            lot_id=request.lot_id,
            serial_number_id=request.serial_number_id,
            notes=request.notes,
        )
        
        return StockMovementResponse(
            stock_movement_id=movement.stock_movement_id,
            occurred_at=movement.occurred_at,
            warehouse_id=movement.warehouse_id,
            source_bin_location_id=movement.source_bin_location_id,
            destination_bin_location_id=movement.destination_bin_location_id,
            item_id=movement.item_id,
            moved_quantity=movement.moved_quantity,
            movement_reason=movement.movement_reason,
            trigger_source=movement.trigger_source,
            notes=movement.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/warehouses/{warehouse_id}/movements", response_model=List[StockMovementResponse])
async def get_movement_history(
    warehouse_id: UUID,
    item_id: Optional[UUID] = None,
    limit: int = 100,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get stock movement history."""
    stock_service = StockService(session)
    

    
    movements = stock_service.get_movement_history(
        warehouse_id=warehouse_id,
        item_id=item_id,
        limit=limit
    )
    
    return [
        StockMovementResponse(
            stock_movement_id=movement.stock_movement_id,
            occurred_at=movement.occurred_at,
            warehouse_id=movement.warehouse_id,
            source_bin_location_id=movement.source_bin_location_id,
            destination_bin_location_id=movement.destination_bin_location_id,
            item_id=movement.item_id,
            moved_quantity=movement.moved_quantity,
            movement_reason=movement.movement_reason,
            trigger_source=movement.trigger_source,
            notes=movement.notes,
        )
        for movement in movements
    ]


@router.post("/sales-orders")
async def create_sales_order(
    request: CreateSalesOrderRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new sales order."""
    sales_service = SalesService(session)
    
    try:
        order = sales_service.create_sales_order(
            warehouse_id=request.warehouse_id,
            sales_order_number=request.sales_order_number,
            order_date=datetime.utcnow(),
            created_by_user_id=current_user.app_user_id,
            external_sales_channel=request.external_sales_channel,
            external_order_identifier=request.external_order_identifier,
            line_items=request.line_items,
        )
        
        return {
            "sales_order_id": str(order.sales_order_id),
            "sales_order_number": order.sales_order_number,
            "status": order.sales_order_status,
            "created_at": order.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sales-orders/{sales_order_id}/allocate")
async def allocate_inventory(
    sales_order_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Allocate inventory for sales order."""
    sales_service = SalesService(session)
    
    try:
        reservations = sales_service.allocate_inventory(
            sales_order_id=sales_order_id,
            actor_user_id=current_user.app_user_id
        )
        
        return {
            "reservations_created": len(reservations),
            "reservation_ids": [str(r.inventory_reservation_id) for r in reservations]
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sales-orders/{sales_order_id}/ship")
async def ship_sales_order(
    sales_order_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Ship sales order."""
    sales_service = SalesService(session)
    
    try:
        movement_ids = sales_service.ship_sales_order(
            sales_order_id=sales_order_id,
            actor_user_id=current_user.app_user_id
        )
        
        return {
            "shipped": True,
            "movement_ids": [str(mid) for mid in movement_ids]
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/warehouses/{warehouse_id}/analytics/sales")
async def get_sales_analytics(
    warehouse_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    group_by: str = "day",
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get sales analytics."""
    analytics_service = AnalyticsService(session)
    
    analytics = analytics_service.get_sales_analytics(
        warehouse_id=warehouse_id,
        user_id=current_user.app_user_id,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )
    
    return {"analytics": analytics}


@router.get("/warehouses/{warehouse_id}/analytics/inventory-turnover")
async def get_inventory_turnover(
    warehouse_id: UUID,
    period_days: int = 90,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get inventory turnover analysis."""
    analytics_service = AnalyticsService(session)
    
    turnover = analytics_service.get_inventory_turnover(
        warehouse_id=warehouse_id,
        user_id=current_user.app_user_id,
        period_days=period_days
    )
    
    return {"turnover_analysis": turnover}


@router.get("/warehouses/{warehouse_id}/analytics/abc-analysis")
async def get_abc_analysis(
    warehouse_id: UUID,
    period_days: int = 365,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get ABC analysis of inventory."""
    analytics_service = AnalyticsService(session)
    
    abc_analysis = analytics_service.get_abc_analysis(
        warehouse_id=warehouse_id,
        user_id=current_user.app_user_id,
        period_days=period_days
    )
    
    return {"abc_analysis": abc_analysis}


@router.post("/warehouses/{warehouse_id}/purchase-recommendations")
async def generate_purchase_recommendations(
    warehouse_id: UUID,
    forecast_days: int = 30,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Generate purchase recommendations."""
    analytics_service = AnalyticsService(session)
    
    recommendations = analytics_service.generate_purchase_recommendations(
        warehouse_id=warehouse_id,
        user_id=current_user.app_user_id,
        forecast_days=forecast_days
    )
    
    return {
        "recommendations_generated": len(recommendations),
        "recommendations": [
            {
                "item_id": str(rec.item_id),
                "recommended_quantity": float(rec.recommended_order_quantity),
                "priority_score": float(rec.priority_score),
                "days_remaining": rec.days_of_stock_remaining,
                "reason": rec.recommendation_reason,
            }
            for rec in recommendations[:20]  # Return top 20
        ]
    }


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user permissions summary."""
    # Simple check - users can view their own permissions, admins can view any
    if user_id != current_user.app_user_id:
        # Would need to implement admin check here
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    from warehouse_service.rbac.unified import RBACService
    rbac = RBACService(session)
    permissions = rbac.get_user_permissions_summary(user_id)
    
    return {"permissions": permissions}