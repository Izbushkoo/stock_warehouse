#!/usr/bin/env python3
"""Test script for unified warehouse system."""

import sys
import os
from decimal import Decimal
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from warehouse_service.db import session_scope, init_db
from warehouse_service.models.unified import (
    Warehouse, Zone, BinLocation, ItemGroup, Item, AppUser,
    StockMovement, StockBalance
)
from warehouse_service.services import StockService, SalesService, AnalyticsService
from warehouse_service.rbac.unified import RBACService, AccessContext, WarehouseOperation


def test_basic_operations():
    """Test basic warehouse operations."""
    print("🧪 Testing unified warehouse system...")
    
    # Initialize database
    print("📊 Initializing database...")
    init_db()
    
    with session_scope() as session:
        # Get test data
        warehouse = session.query(Warehouse).filter_by(warehouse_code="WH001").first()
        if not warehouse:
            print("❌ No test warehouse found. Run migrations first.")
            return False
        
        user = session.query(AppUser).filter_by(user_email="admin@warehouse.local").first()
        if not user:
            print("❌ No test user found. Run migrations first.")
            return False
        
        item = session.query(Item).first()
        if not item:
            print("❌ No test items found. Run migrations first.")
            return False
        
        # Get a storage bin
        storage_zone = session.query(Zone).filter_by(
            warehouse_id=warehouse.warehouse_id,
            zone_function="storage"
        ).first()
        
        storage_bin = session.query(BinLocation).filter_by(
            zone_id=storage_zone.zone_id
        ).first()
        
        print(f"✅ Found test data:")
        print(f"   - Warehouse: {warehouse.warehouse_name}")
        print(f"   - User: {user.user_display_name}")
        print(f"   - Item: {item.item_name} ({item.stock_keeping_unit})")
        print(f"   - Storage bin: {storage_bin.bin_location_code}")
        
        # Test RBAC
        print("\n🔐 Testing RBAC system...")
        rbac = RBACService(session)
        
        context = AccessContext(
            warehouse_id=warehouse.warehouse_id,
            item_group_id=item.item_group_id
        )
        
        can_view = rbac.check_permission(user.app_user_id, WarehouseOperation.VIEW_INVENTORY, context)
        can_create = rbac.check_permission(user.app_user_id, WarehouseOperation.CREATE_MOVEMENT, context)
        can_approve = rbac.check_permission(user.app_user_id, WarehouseOperation.APPROVE_MOVEMENT, context)
        
        print(f"   - Can view inventory: {can_view}")
        print(f"   - Can create movements: {can_create}")
        print(f"   - Can approve movements: {can_approve}")
        
        if not can_create:
            print("❌ User doesn't have permission to create movements")
            return False
        
        # Test stock service
        print("\n📦 Testing stock operations...")
        stock_service = StockService(session)
        
        # Create goods receipt
        print("   - Creating goods receipt...")
        receipt_movement = stock_service.create_stock_movement(
            warehouse_id=warehouse.warehouse_id,
            source_bin_location_id=None,  # External world
            destination_bin_location_id=storage_bin.bin_location_id,
            item_id=item.item_id,
            moved_quantity=Decimal('100'),
            movement_reason="goods_receipt",
            actor_user_id=user.app_user_id,
            trigger_source=f"test:user:{user.app_user_id}",
            notes="Test goods receipt"
        )
        
        print(f"     ✅ Created movement: {receipt_movement.stock_movement_id}")
        
        # Check stock balance
        balances = stock_service.get_stock_balance(
            warehouse_id=warehouse.warehouse_id,
            item_id=item.item_id,
            user_id=user.app_user_id
        )
        
        print(f"   - Current stock balance: {len(balances)} records")
        for balance in balances:
            print(f"     - Bin {balance.bin_location_id}: {balance.quantity_on_hand} on hand, {balance.quantity_reserved} reserved")
        
        # Test internal transfer
        print("   - Creating internal transfer...")
        
        # Get another bin for transfer
        picking_zone = session.query(Zone).filter_by(
            warehouse_id=warehouse.warehouse_id,
            zone_function="picking"
        ).first()
        
        picking_bin = session.query(BinLocation).filter_by(
            zone_id=picking_zone.zone_id
        ).first()
        
        transfer_movement = stock_service.process_internal_transfer(
            warehouse_id=warehouse.warehouse_id,
            source_bin_location_id=storage_bin.bin_location_id,
            destination_bin_location_id=picking_bin.bin_location_id,
            item_id=item.item_id,
            quantity=Decimal('20'),
            actor_user_id=user.app_user_id,
            notes="Test internal transfer"
        )
        
        print(f"     ✅ Created transfer: {transfer_movement.stock_movement_id}")
        
        # Test sales service
        print("\n🛒 Testing sales operations...")
        sales_service = SalesService(session)
        
        # Create sales order
        print("   - Creating sales order...")
        sales_order = sales_service.create_sales_order(
            warehouse_id=warehouse.warehouse_id,
            sales_order_number=f"SO-{uuid4().hex[:8].upper()}",
            order_date=receipt_movement.occurred_at,
            created_by_user_id=user.app_user_id,
            external_sales_channel="test_marketplace",
            line_items=[{
                "item_id": item.item_id,
                "quantity": Decimal('5'),
                "unit_price": Decimal('29.99')
            }]
        )
        
        print(f"     ✅ Created order: {sales_order.sales_order_number}")
        
        # Allocate inventory
        print("   - Allocating inventory...")
        reservations = sales_service.allocate_inventory(
            sales_order_id=sales_order.sales_order_id,
            actor_user_id=user.app_user_id
        )
        
        print(f"     ✅ Created {len(reservations)} reservations")
        
        # Ship order
        print("   - Shipping order...")
        movement_ids = sales_service.ship_sales_order(
            sales_order_id=sales_order.sales_order_id,
            actor_user_id=user.app_user_id
        )
        
        print(f"     ✅ Created {len(movement_ids)} shipping movements")
        
        # Test analytics
        print("\n📊 Testing analytics...")
        analytics_service = AnalyticsService(session)
        
        # Get sales analytics
        sales_analytics = analytics_service.get_sales_analytics(
            warehouse_id=warehouse.warehouse_id,
            user_id=user.app_user_id,
            group_by="total"
        )
        
        print(f"   - Sales analytics: {len(sales_analytics)} records")
        for record in sales_analytics:
            print(f"     - Total revenue: ${record.get('total_revenue', 0):.2f}")
            print(f"     - Total quantity: {record.get('total_quantity', 0)}")
        
        # Get inventory turnover
        turnover = analytics_service.get_inventory_turnover(
            warehouse_id=warehouse.warehouse_id,
            user_id=user.app_user_id,
            period_days=30
        )
        
        print(f"   - Inventory turnover: {len(turnover)} items analyzed")
        for item_turnover in turnover[:3]:  # Show top 3
            print(f"     - {item_turnover['item_name']}: {item_turnover['turnover_rate']:.2f} turns")
        
        # Generate purchase recommendations
        print("   - Generating purchase recommendations...")
        recommendations = analytics_service.generate_purchase_recommendations(
            warehouse_id=warehouse.warehouse_id,
            user_id=user.app_user_id,
            forecast_days=30
        )
        
        print(f"     ✅ Generated {len(recommendations)} recommendations")
        for rec in recommendations[:3]:  # Show top 3
            print(f"       - Item {rec.item_id}: order {rec.recommended_order_quantity}, priority {rec.priority_score}")
        
        # Final stock check
        print("\n📋 Final stock check...")
        final_balances = stock_service.get_stock_balance(
            warehouse_id=warehouse.warehouse_id,
            user_id=user.app_user_id
        )
        
        total_stock = sum(balance.quantity_on_hand for balance in final_balances)
        total_reserved = sum(balance.quantity_reserved for balance in final_balances)
        
        print(f"   - Total stock on hand: {total_stock}")
        print(f"   - Total reserved: {total_reserved}")
        print(f"   - Available stock: {total_stock - total_reserved}")
        
        print("\n✅ All tests completed successfully!")
        return True


if __name__ == "__main__":
    try:
        success = test_basic_operations()
        if success:
            print("\n🎉 Unified warehouse system is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)