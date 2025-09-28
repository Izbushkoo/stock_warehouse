"""Stock movement and inventory management service."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select, func

from warehouse_service.models.unified import (
    StockMovement, StockBalance, Item, Warehouse, BinLocation, 
    Lot, SerialNumber, AppUser, AuditLog, DomainEvent
)



class StockService:
    """Service for stock movement and inventory operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_stock_movement(
        self,
        warehouse_id: UUID,
        item_id: UUID,
        moved_quantity: Decimal,
        movement_reason: str,
        actor_user_id: UUID,
        trigger_source: str,
        source_bin_location_id: Optional[UUID] = None,
        destination_bin_location_id: Optional[UUID] = None,
        lot_id: Optional[UUID] = None,
        serial_number_id: Optional[UUID] = None,
        unit_of_measure: str = "pieces",
        document_type: Optional[str] = None,
        document_identifier: Optional[UUID] = None,
        transaction_group: Optional[UUID] = None,
        correlation_identifier: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """Create a new stock movement and update balances."""
        
        # Validate business rules
        self._validate_movement_request(
            warehouse_id, item_id, moved_quantity, movement_reason,
            source_bin_location_id, destination_bin_location_id,
            lot_id, serial_number_id
        )
        
        # Validate item exists
        item = self.session.get(Item, item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        
        # Create the movement
        movement = StockMovement(
            warehouse_id=warehouse_id,
            source_bin_location_id=source_bin_location_id,
            destination_bin_location_id=destination_bin_location_id,
            item_id=item_id,
            lot_id=lot_id,
            serial_number_id=serial_number_id,
            moved_quantity=moved_quantity,
            unit_of_measure=unit_of_measure,
            movement_reason=movement_reason,
            document_type=document_type,
            document_identifier=document_identifier,
            actor_user_id=actor_user_id,
            trigger_source=trigger_source,
            transaction_group=transaction_group or uuid4(),
            correlation_identifier=correlation_identifier or uuid4(),
            notes=notes,
        )
        
        self.session.add(movement)
        self.session.flush()  # Get the ID
        
        # Update stock balances
        self._update_stock_balances(movement)
        
        # Create audit log
        self._create_audit_log(
            actor_user_id=actor_user_id,
            action="CREATE_STOCK_MOVEMENT",
            entity_table="stock_movement",
            entity_id=movement.stock_movement_id,
            after_state=movement.dict(),
            correlation_identifier=correlation_identifier,
        )
        
        # Create domain event
        self._create_domain_event(
            event_name="StockMovementCreated",
            aggregate_type="stock_movement",
            aggregate_id=movement.stock_movement_id,
            payload={
                "movement_reason": movement_reason,
                "item_id": str(item_id),
                "warehouse_id": str(warehouse_id),
                "moved_quantity": float(moved_quantity),
                "trigger_source": trigger_source,
            },
            actor_user_id=actor_user_id,
            transaction_group=movement.transaction_group,
            correlation_identifier=correlation_identifier,
        )
        
        self.session.commit()
        self.session.refresh(movement)
        return movement
    
    def get_stock_balance(
        self,
        warehouse_id: UUID,
        item_id: Optional[UUID] = None,
        bin_location_id: Optional[UUID] = None,
        lot_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> List[StockBalance]:
        """Get current stock balances with optional filtering."""
        
        stmt = select(StockBalance).where(StockBalance.warehouse_id == warehouse_id)
        
        if item_id:
            stmt = stmt.where(StockBalance.item_id == item_id)
        if bin_location_id:
            stmt = stmt.where(StockBalance.bin_location_id == bin_location_id)
        if lot_id:
            stmt = stmt.where(StockBalance.lot_id == lot_id)
        
        # Filter by user permissions if provided
        if user_id:
            accessible_item_groups = self.rbac.get_accessible_item_groups(user_id, warehouse_id)
            if accessible_item_groups:
                # Join with Item to filter by item_group
                stmt = stmt.join(Item).where(Item.item_group_id.in_(accessible_item_groups))
        
        balances = list(self.session.exec(stmt))
        return [b for b in balances if b.quantity_on_hand > 0]
    
    def get_movement_history(
        self,
        warehouse_id: UUID,
        item_id: Optional[UUID] = None,
        bin_location_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[StockMovement]:
        """Get stock movement history with filtering."""
        
        stmt = select(StockMovement).where(StockMovement.warehouse_id == warehouse_id)
        
        if item_id:
            stmt = stmt.where(StockMovement.item_id == item_id)
        if bin_location_id:
            stmt = stmt.where(
                (StockMovement.source_bin_location_id == bin_location_id) |
                (StockMovement.destination_bin_location_id == bin_location_id)
            )
        if start_date:
            stmt = stmt.where(StockMovement.occurred_at >= start_date)
        if end_date:
            stmt = stmt.where(StockMovement.occurred_at <= end_date)
        
        stmt = stmt.order_by(StockMovement.occurred_at.desc()).limit(limit)
        
        return list(self.session.exec(stmt))
    
    def process_goods_receipt(
        self,
        warehouse_id: UUID,
        destination_bin_location_id: UUID,
        items: List[dict],  # [{"item_id": UUID, "quantity": Decimal, "lot_code": str, ...}]
        actor_user_id: UUID,
        receipt_file_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> List[StockMovement]:
        """Process goods receipt from external supplier."""
        
        movements = []
        transaction_group = uuid4()
        correlation_identifier = uuid4()
        
        for item_data in items:
            # Handle lot creation if needed
            lot_id = None
            if item_data.get("lot_code"):
                lot_id = self._ensure_lot_exists(
                    item_data["item_id"], 
                    item_data["lot_code"],
                    item_data.get("manufactured_at"),
                    item_data.get("expiration_date"),
                )
            
            # Handle serial numbers if needed
            serial_number_id = None
            if item_data.get("serial_code"):
                serial_number_id = self._ensure_serial_number_exists(
                    item_data["item_id"],
                    item_data["serial_code"],
                    lot_id,
                )
            
            movement = self.create_stock_movement(
                warehouse_id=warehouse_id,
                source_bin_location_id=None,  # External world
                destination_bin_location_id=destination_bin_location_id,
                item_id=item_data["item_id"],
                lot_id=lot_id,
                serial_number_id=serial_number_id,
                moved_quantity=item_data["quantity"],
                movement_reason="goods_receipt",
                actor_user_id=actor_user_id,
                trigger_source=f"user:{actor_user_id}",
                document_type="receipt_file" if receipt_file_id else None,
                document_identifier=receipt_file_id,
                transaction_group=transaction_group,
                correlation_identifier=correlation_identifier,
                notes=notes,
            )
            movements.append(movement)
        
        return movements
    
    def process_sales_issue(
        self,
        warehouse_id: UUID,
        source_bin_location_id: UUID,
        items: List[dict],  # [{"item_id": UUID, "quantity": Decimal, "lot_id": UUID, ...}]
        sales_order_id: UUID,
        actor_user_id: UUID,
        notes: Optional[str] = None,
    ) -> List[StockMovement]:
        """Process sales issue/shipment."""
        
        movements = []
        transaction_group = uuid4()
        correlation_identifier = uuid4()
        
        for item_data in items:
            movement = self.create_stock_movement(
                warehouse_id=warehouse_id,
                source_bin_location_id=source_bin_location_id,
                destination_bin_location_id=None,  # External world
                item_id=item_data["item_id"],
                lot_id=item_data.get("lot_id"),
                serial_number_id=item_data.get("serial_number_id"),
                moved_quantity=-abs(item_data["quantity"]),  # Negative for outbound
                movement_reason="sales_issue",
                actor_user_id=actor_user_id,
                trigger_source=f"sales_order:{sales_order_id}",
                document_type="sales_order",
                document_identifier=sales_order_id,
                transaction_group=transaction_group,
                correlation_identifier=correlation_identifier,
                notes=notes,
            )
            movements.append(movement)
        
        return movements
    
    def process_internal_transfer(
        self,
        warehouse_id: UUID,
        source_bin_location_id: UUID,
        destination_bin_location_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        actor_user_id: UUID,
        lot_id: Optional[UUID] = None,
        serial_number_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """Process internal transfer between bin locations."""
        
        return self.create_stock_movement(
            warehouse_id=warehouse_id,
            source_bin_location_id=source_bin_location_id,
            destination_bin_location_id=destination_bin_location_id,
            item_id=item_id,
            lot_id=lot_id,
            serial_number_id=serial_number_id,
            moved_quantity=quantity,
            movement_reason="internal_transfer",
            actor_user_id=actor_user_id,
            trigger_source=f"user:{actor_user_id}",
            notes=notes,
        )
    
    def process_manual_adjustment(
        self,
        warehouse_id: UUID,
        bin_location_id: UUID,
        item_id: UUID,
        adjustment_quantity: Decimal,
        reason: str,
        actor_user_id: UUID,
        lot_id: Optional[UUID] = None,
        serial_number_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """Process manual stock adjustment."""
        
        # Check approval permission for manual adjustments
        item = self.session.get(Item, item_id)

        
        # Determine source/destination based on adjustment direction
        source_bin = bin_location_id if adjustment_quantity < 0 else None
        dest_bin = bin_location_id if adjustment_quantity > 0 else None
        
        return self.create_stock_movement(
            warehouse_id=warehouse_id,
            source_bin_location_id=source_bin,
            destination_bin_location_id=dest_bin,
            item_id=item_id,
            lot_id=lot_id,
            serial_number_id=serial_number_id,
            moved_quantity=adjustment_quantity,
            movement_reason="manual_adjustment",
            actor_user_id=actor_user_id,
            trigger_source=f"user:{actor_user_id}",
            notes=f"{reason}: {notes}" if notes else reason,
        )
    
    def _validate_movement_request(
        self,
        warehouse_id: UUID,
        item_id: UUID,
        moved_quantity: Decimal,
        movement_reason: str,
        source_bin_location_id: Optional[UUID],
        destination_bin_location_id: Optional[UUID],
        lot_id: Optional[UUID],
        serial_number_id: Optional[UUID],
    ):
        """Validate movement request against business rules."""
        
        # Validate warehouse exists
        warehouse = self.session.get(Warehouse, warehouse_id)
        if not warehouse or not warehouse.is_active:
            raise ValueError(f"Warehouse {warehouse_id} not found or inactive")
        
        # Validate item exists and is active
        item = self.session.get(Item, item_id)
        if not item or item.item_status != "active":
            raise ValueError(f"Item {item_id} not found or inactive")
        
        # Validate lot tracking requirements
        if item.is_lot_tracked and not lot_id:
            raise ValueError(f"Item {item_id} requires lot tracking but no lot_id provided")
        
        # Validate serial number tracking requirements
        if item.is_serial_number_tracked and not serial_number_id:
            raise ValueError(f"Item {item_id} requires serial number tracking but no serial_number_id provided")
        
        # Validate serial number quantity consistency
        if serial_number_id and abs(moved_quantity) != 1:
            raise ValueError("Serial number tracked items must have quantity of 1")
        
        # Validate bin locations exist if provided
        if source_bin_location_id:
            source_bin = self.session.get(BinLocation, source_bin_location_id)
            if not source_bin or source_bin.warehouse_id != warehouse_id:
                raise ValueError(f"Source bin location {source_bin_location_id} not found in warehouse")
        
        if destination_bin_location_id:
            dest_bin = self.session.get(BinLocation, destination_bin_location_id)
            if not dest_bin or dest_bin.warehouse_id != warehouse_id:
                raise ValueError(f"Destination bin location {destination_bin_location_id} not found in warehouse")
        
        # Validate sufficient stock for outbound movements
        if source_bin_location_id and moved_quantity < 0:
            available = self._get_available_quantity(
                warehouse_id, source_bin_location_id, item_id, lot_id, serial_number_id
            )
            if available < abs(moved_quantity):
                raise ValueError(f"Insufficient stock: available {available}, requested {abs(moved_quantity)}")
    
    def _update_stock_balances(self, movement: StockMovement):
        """Update stock balances based on movement."""
        
        # Handle outbound (from source)
        if movement.source_bin_location_id:
            self._update_balance_record(
                movement.warehouse_id,
                movement.source_bin_location_id,
                movement.item_id,
                movement.lot_id,
                movement.serial_number_id,
                -abs(movement.moved_quantity),  # Always negative for outbound
                movement.occurred_at,
            )
        
        # Handle inbound (to destination)
        if movement.destination_bin_location_id:
            self._update_balance_record(
                movement.warehouse_id,
                movement.destination_bin_location_id,
                movement.item_id,
                movement.lot_id,
                movement.serial_number_id,
                abs(movement.moved_quantity),  # Always positive for inbound
                movement.occurred_at,
            )
    
    def _update_balance_record(
        self,
        warehouse_id: UUID,
        bin_location_id: UUID,
        item_id: UUID,
        lot_id: Optional[UUID],
        serial_number_id: Optional[UUID],
        quantity_change: Decimal,
        movement_time: datetime,
    ):
        """Update or create stock balance record."""
        
        # Find existing balance record
        stmt = select(StockBalance).where(
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.bin_location_id == bin_location_id,
            StockBalance.item_id == item_id,
            StockBalance.lot_id == lot_id,
            StockBalance.serial_number_id == serial_number_id,
        )
        
        balance = self.session.exec(stmt).first()
        
        if balance:
            # Update existing balance
            balance.quantity_on_hand += quantity_change
            balance.last_movement_at = movement_time
        else:
            # Create new balance record
            balance = StockBalance(
                warehouse_id=warehouse_id,
                bin_location_id=bin_location_id,
                item_id=item_id,
                lot_id=lot_id,
                serial_number_id=serial_number_id,
                quantity_on_hand=quantity_change,
                quantity_reserved=Decimal('0'),
                last_movement_at=movement_time,
            )
            self.session.add(balance)
        
        # Validate balance doesn't go negative
        if balance.quantity_on_hand < 0:
            raise ValueError(f"Stock balance would go negative: {balance.quantity_on_hand}")
    
    def _get_available_quantity(
        self,
        warehouse_id: UUID,
        bin_location_id: UUID,
        item_id: UUID,
        lot_id: Optional[UUID],
        serial_number_id: Optional[UUID],
    ) -> Decimal:
        """Get available quantity (on_hand - reserved)."""
        
        stmt = select(StockBalance).where(
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.bin_location_id == bin_location_id,
            StockBalance.item_id == item_id,
            StockBalance.lot_id == lot_id,
            StockBalance.serial_number_id == serial_number_id,
        )
        
        balance = self.session.exec(stmt).first()
        if not balance:
            return Decimal('0')
        
        return balance.quantity_on_hand - balance.quantity_reserved
    
    def _ensure_lot_exists(
        self,
        item_id: UUID,
        lot_code: str,
        manufactured_at: Optional[datetime] = None,
        expiration_date: Optional[datetime] = None,
    ) -> UUID:
        """Ensure lot exists, create if not found."""
        
        stmt = select(Lot).where(
            Lot.item_id == item_id,
            Lot.lot_code == lot_code,
        )
        
        lot = self.session.exec(stmt).first()
        if not lot:
            lot = Lot(
                item_id=item_id,
                lot_code=lot_code,
                manufactured_at=manufactured_at.date() if manufactured_at else None,
                expiration_date=expiration_date.date() if expiration_date else None,
            )
            self.session.add(lot)
            self.session.flush()
        
        return lot.lot_id
    
    def _ensure_serial_number_exists(
        self,
        item_id: UUID,
        serial_code: str,
        lot_id: Optional[UUID] = None,
    ) -> UUID:
        """Ensure serial number exists, create if not found."""
        
        stmt = select(SerialNumber).where(SerialNumber.serial_code == serial_code)
        
        serial = self.session.exec(stmt).first()
        if not serial:
            serial = SerialNumber(
                item_id=item_id,
                serial_code=serial_code,
                lot_id=lot_id,
                serial_status="in_stock",
            )
            self.session.add(serial)
            self.session.flush()
        
        return serial.serial_number_id
    
    def _create_audit_log(
        self,
        actor_user_id: UUID,
        action: str,
        entity_table: str,
        entity_id: UUID,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        correlation_identifier: Optional[UUID] = None,
    ):
        """Create audit log entry."""
        
        audit = AuditLog(
            actor_user_id=actor_user_id,
            audited_action=action,
            entity_table_name=entity_table,
            entity_primary_identifier=entity_id,
            before_state=before_state,
            after_state=after_state,
            correlation_identifier=correlation_identifier,
        )
        
        self.session.add(audit)
    
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