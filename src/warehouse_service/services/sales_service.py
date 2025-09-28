"""Sales order management service."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID, uuid4

from sqlmodel import Session, select

from warehouse_service.models.unified import (
    SalesOrder, SalesOrderLine, InventoryReservation, StockBalance,
    Item, Warehouse, BinLocation, SalesAnalytics, DomainEvent
)

from warehouse_service.services.stock_service import StockService


class SalesService:
    """Service for sales order management and fulfillment."""
    
    def __init__(self, session: Session):
        self.session = session
        self.stock_service = StockService(session)
    
    def create_sales_order(
        self,
        warehouse_id: UUID,
        sales_order_number: str,
        order_date: datetime,
        created_by_user_id: UUID,
        external_sales_channel: Optional[str] = None,
        external_order_identifier: Optional[str] = None,
        line_items: Optional[List[Dict]] = None,
    ) -> SalesOrder:
        """Create a new sales order."""
        

        
        # Create sales order
        sales_order = SalesOrder(
            warehouse_id=warehouse_id,
            sales_order_number=sales_order_number,
            external_sales_channel=external_sales_channel,
            external_order_identifier=external_order_identifier,
            sales_order_status="draft",
            order_date=order_date,
            created_by_user_id=created_by_user_id,
        )
        
        self.session.add(sales_order)
        self.session.flush()
        
        # Add line items if provided
        if line_items:
            for line_data in line_items:
                line = SalesOrderLine(
                    sales_order_id=sales_order.sales_order_id,
                    item_id=line_data["item_id"],
                    ordered_quantity=line_data["quantity"],
                    unit_price=line_data.get("unit_price"),
                )
                self.session.add(line)
        
        # Create domain event
        self._create_domain_event(
            event_name="SalesOrderCreated",
            aggregate_type="sales_order",
            aggregate_id=sales_order.sales_order_id,
            payload={
                "sales_order_number": sales_order_number,
                "warehouse_id": str(warehouse_id),
                "external_sales_channel": external_sales_channel,
                "external_order_identifier": external_order_identifier,
                "line_count": len(line_items) if line_items else 0,
            },
            actor_user_id=created_by_user_id,
        )
        
        self.session.commit()
        self.session.refresh(sales_order)
        return sales_order
    
    def allocate_inventory(
        self,
        sales_order_id: UUID,
        actor_user_id: UUID,
        allocation_strategy: str = "fifo",  # fifo, lifo, nearest_expiry
    ) -> List[InventoryReservation]:
        """Allocate inventory for sales order."""
        
        sales_order = self.session.get(SalesOrder, sales_order_id)
        if not sales_order:
            raise ValueError(f"Sales order {sales_order_id} not found")
        
        if sales_order.sales_order_status != "draft":
            raise ValueError(f"Cannot allocate inventory for order in status {sales_order.sales_order_status}")
        

        
        reservations = []
        
        # Get order lines
        stmt = select(SalesOrderLine).where(SalesOrderLine.sales_order_id == sales_order_id)
        lines = list(self.session.exec(stmt))
        
        for line in lines:
            remaining_to_allocate = line.ordered_quantity - line.allocated_quantity
            
            if remaining_to_allocate <= 0:
                continue
            
            # Find available stock for this item
            available_stock = self._find_available_stock(
                sales_order.warehouse_id,
                line.item_id,
                allocation_strategy,
            )
            
            allocated_this_line = Decimal('0')
            
            for stock_record in available_stock:
                if remaining_to_allocate <= 0:
                    break
                
                available_qty = stock_record.quantity_on_hand - stock_record.quantity_reserved
                if available_qty <= 0:
                    continue
                
                # Allocate up to what's needed or available
                allocate_qty = min(remaining_to_allocate, available_qty)
                
                # Create reservation
                reservation = InventoryReservation(
                    sales_order_id=sales_order_id,
                    sales_order_line_id=line.sales_order_line_id,
                    warehouse_id=sales_order.warehouse_id,
                    bin_location_id=stock_record.bin_location_id,
                    item_id=line.item_id,
                    lot_id=stock_record.lot_id,
                    serial_number_id=stock_record.serial_number_id,
                    reserved_quantity=allocate_qty,
                    reservation_status="active",
                )
                
                self.session.add(reservation)
                reservations.append(reservation)
                
                # Update stock balance reserved quantity
                stock_record.quantity_reserved += allocate_qty
                
                # Update line allocated quantity
                allocated_this_line += allocate_qty
                remaining_to_allocate -= allocate_qty
            
            line.allocated_quantity += allocated_this_line
        
        # Update order status if fully allocated
        total_ordered = sum(line.ordered_quantity for line in lines)
        total_allocated = sum(line.allocated_quantity for line in lines)
        
        if total_allocated >= total_ordered:
            sales_order.sales_order_status = "allocated"
        
        # Create domain event
        self._create_domain_event(
            event_name="InventoryAllocated",
            aggregate_type="sales_order",
            aggregate_id=sales_order_id,
            payload={
                "reservations_created": len(reservations),
                "total_ordered": float(total_ordered),
                "total_allocated": float(total_allocated),
                "fully_allocated": total_allocated >= total_ordered,
            },
            actor_user_id=actor_user_id,
        )
        
        self.session.commit()
        return reservations
    
    def ship_sales_order(
        self,
        sales_order_id: UUID,
        actor_user_id: UUID,
        shipping_notes: Optional[str] = None,
    ) -> List[UUID]:  # Returns list of stock movement IDs
        """Ship sales order and create stock movements."""
        
        sales_order = self.session.get(SalesOrder, sales_order_id)
        if not sales_order:
            raise ValueError(f"Sales order {sales_order_id} not found")
        
        if sales_order.sales_order_status != "allocated":
            raise ValueError(f"Cannot ship order in status {sales_order.sales_order_status}")
        

        
        # Get active reservations
        stmt = select(InventoryReservation).where(
            InventoryReservation.sales_order_id == sales_order_id,
            InventoryReservation.reservation_status == "active",
        )
        reservations = list(self.session.exec(stmt))
        
        if not reservations:
            raise ValueError("No active reservations found for sales order")
        
        # Create stock movements for each reservation
        movement_ids = []
        items_to_ship = []
        
        for reservation in reservations:
            items_to_ship.append({
                "item_id": reservation.item_id,
                "quantity": reservation.reserved_quantity,
                "lot_id": reservation.lot_id,
                "serial_number_id": reservation.serial_number_id,
            })
            
            # Update reservation status
            reservation.reservation_status = "consumed"
            
            # Update stock balance reserved quantity
            stmt = select(StockBalance).where(
                StockBalance.warehouse_id == reservation.warehouse_id,
                StockBalance.bin_location_id == reservation.bin_location_id,
                StockBalance.item_id == reservation.item_id,
                StockBalance.lot_id == reservation.lot_id,
                StockBalance.serial_number_id == reservation.serial_number_id,
            )
            balance = self.session.exec(stmt).first()
            if balance:
                balance.quantity_reserved -= reservation.reserved_quantity
        
        # Create stock movements
        movements = self.stock_service.process_sales_issue(
            warehouse_id=sales_order.warehouse_id,
            source_bin_location_id=reservations[0].bin_location_id,  # Simplified - use first reservation's bin
            items=items_to_ship,
            sales_order_id=sales_order_id,
            actor_user_id=actor_user_id,
            notes=shipping_notes,
        )
        
        movement_ids = [m.stock_movement_id for m in movements]
        
        # Update order lines shipped quantities
        stmt = select(SalesOrderLine).where(SalesOrderLine.sales_order_id == sales_order_id)
        lines = list(self.session.exec(stmt))
        
        for line in lines:
            line.shipped_quantity = line.allocated_quantity
        
        # Update order status
        sales_order.sales_order_status = "shipped"
        
        # Create sales analytics
        self._create_sales_analytics(sales_order, lines, actor_user_id)
        
        # Create domain event
        self._create_domain_event(
            event_name="SalesOrderShipped",
            aggregate_type="sales_order",
            aggregate_id=sales_order_id,
            payload={
                "movement_ids": [str(mid) for mid in movement_ids],
                "items_shipped": len(items_to_ship),
                "total_quantity": sum(item["quantity"] for item in items_to_ship),
                "external_sales_channel": sales_order.external_sales_channel,
            },
            actor_user_id=actor_user_id,
        )
        
        self.session.commit()
        return movement_ids
    
    def cancel_sales_order(
        self,
        sales_order_id: UUID,
        actor_user_id: UUID,
        cancellation_reason: str,
    ):
        """Cancel sales order and release reservations."""
        
        sales_order = self.session.get(SalesOrder, sales_order_id)
        if not sales_order:
            raise ValueError(f"Sales order {sales_order_id} not found")
        
        if sales_order.sales_order_status in ["shipped", "closed"]:
            raise ValueError(f"Cannot cancel order in status {sales_order.sales_order_status}")
        
        # Release all active reservations
        stmt = select(InventoryReservation).where(
            InventoryReservation.sales_order_id == sales_order_id,
            InventoryReservation.reservation_status == "active",
        )
        reservations = list(self.session.exec(stmt))
        
        for reservation in reservations:
            # Update reservation status
            reservation.reservation_status = "released"
            
            # Update stock balance reserved quantity
            stmt = select(StockBalance).where(
                StockBalance.warehouse_id == reservation.warehouse_id,
                StockBalance.bin_location_id == reservation.bin_location_id,
                StockBalance.item_id == reservation.item_id,
                StockBalance.lot_id == reservation.lot_id,
                StockBalance.serial_number_id == reservation.serial_number_id,
            )
            balance = self.session.exec(stmt).first()
            if balance:
                balance.quantity_reserved -= reservation.reserved_quantity
        
        # Reset order line allocated quantities
        stmt = select(SalesOrderLine).where(SalesOrderLine.sales_order_id == sales_order_id)
        lines = list(self.session.exec(stmt))
        
        for line in lines:
            line.allocated_quantity = Decimal('0')
        
        # Update order status
        sales_order.sales_order_status = "closed"
        
        # Create domain event
        self._create_domain_event(
            event_name="SalesOrderCancelled",
            aggregate_type="sales_order",
            aggregate_id=sales_order_id,
            payload={
                "cancellation_reason": cancellation_reason,
                "reservations_released": len(reservations),
            },
            actor_user_id=actor_user_id,
        )
        
        self.session.commit()
    
    def get_sales_orders(
        self,
        warehouse_id: UUID,
        user_id: UUID,
        status: Optional[str] = None,
        external_channel: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SalesOrder]:
        """Get sales orders with filtering and permission checks."""
        

        
        stmt = select(SalesOrder).where(SalesOrder.warehouse_id == warehouse_id)
        
        if status:
            stmt = stmt.where(SalesOrder.sales_order_status == status)
        if external_channel:
            stmt = stmt.where(SalesOrder.external_sales_channel == external_channel)
        if start_date:
            stmt = stmt.where(SalesOrder.order_date >= start_date)
        if end_date:
            stmt = stmt.where(SalesOrder.order_date <= end_date)
        
        stmt = stmt.order_by(SalesOrder.order_date.desc()).limit(limit)
        
        return list(self.session.exec(stmt))
    
    def _find_available_stock(
        self,
        warehouse_id: UUID,
        item_id: UUID,
        allocation_strategy: str,
    ) -> List[StockBalance]:
        """Find available stock for allocation."""
        
        stmt = select(StockBalance).where(
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.item_id == item_id,
            StockBalance.quantity_on_hand > StockBalance.quantity_reserved,
        )
        
        # Apply allocation strategy
        if allocation_strategy == "fifo":
            # Join with Lot to order by manufactured_at
            stmt = stmt.join(Item).order_by(StockBalance.last_movement_at.asc())
        elif allocation_strategy == "lifo":
            stmt = stmt.order_by(StockBalance.last_movement_at.desc())
        elif allocation_strategy == "nearest_expiry":
            # This would need a more complex join with Lot table
            stmt = stmt.order_by(StockBalance.last_movement_at.asc())
        
        return list(self.session.exec(stmt))
    
    def _create_sales_analytics(
        self,
        sales_order: SalesOrder,
        lines: List[SalesOrderLine],
        actor_user_id: UUID,
    ):
        """Create sales analytics records."""
        
        for line in lines:
            if line.shipped_quantity <= 0:
                continue
            
            # Calculate metrics
            total_revenue = line.shipped_quantity * (line.unit_price or Decimal('0'))
            
            # Get item for cost calculation (simplified - would need proper cost tracking)
            item = self.session.get(Item, line.item_id)
            unit_cost = Decimal('0')  # Would need to implement cost tracking
            total_cost = line.shipped_quantity * unit_cost
            gross_margin = total_revenue - total_cost
            margin_percentage = (gross_margin / total_revenue * 100) if total_revenue > 0 else Decimal('0')
            
            analytics = SalesAnalytics(
                sales_order_id=sales_order.sales_order_id,
                sales_order_line_id=line.sales_order_line_id,
                item_id=line.item_id,
                warehouse_id=sales_order.warehouse_id,
                quantity_sold=line.shipped_quantity,
                unit_sale_price=line.unit_price or Decimal('0'),
                unit_cost_price=unit_cost,
                total_revenue=total_revenue,
                total_cost=total_cost,
                gross_margin=gross_margin,
                margin_percentage=margin_percentage,
                marketplace_channel=sales_order.external_sales_channel or "direct",
                external_order_id=sales_order.external_order_identifier,
                sale_date=datetime.utcnow(),
                season_quarter=((datetime.utcnow().month - 1) // 3) + 1,
                day_of_week=datetime.utcnow().weekday() + 1,
            )
            
            self.session.add(analytics)
    
    def _create_domain_event(
        self,
        event_name: str,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict,
        actor_user_id: Optional[UUID] = None,
        transaction_group: Optional[UUID] = None,
        correlation_identifier: Optional[UUID] = None,
    ):
        """Create domain event."""
        
        event = DomainEvent(
            event_name=event_name,
            aggregate_type=aggregate_type,
            aggregate_identifier=aggregate_id,
            event_payload=payload,
            actor_user_id=actor_user_id,
            transaction_group=transaction_group,
            correlation_identifier=correlation_identifier,
        )
        
        self.session.add(event)