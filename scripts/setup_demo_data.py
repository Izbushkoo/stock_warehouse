#!/usr/bin/env python3
"""Setup demo data for unified warehouse system."""

import sys
import os
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from warehouse_service.db import session_scope
from warehouse_service.models.unified import (
    Warehouse, Zone, BinLocation, ItemGroup, Item, AppUser, WarehouseAccessGrant
)


def create_demo_data():
    """Create demo data for testing."""
    print("🎭 Creating demo data for unified warehouse system...")
    
    with session_scope() as session:
        # Check if data already exists
        existing_warehouse = session.query(Warehouse).first()
        if existing_warehouse:
            print("⚠️ Demo data already exists. Skipping creation.")
            return True
        
        print("📦 Creating warehouses...")
        warehouses = [
            Warehouse(
                warehouse_code="WH001",
                warehouse_name="Main Warehouse Moscow",
                warehouse_address="Moscow, Russia",
                time_zone="Europe/Moscow",
                is_active=True
            ),
            Warehouse(
                warehouse_code="WH002", 
                warehouse_name="Distribution Center SPB",
                warehouse_address="Saint Petersburg, Russia",
                time_zone="Europe/Moscow",
                is_active=True
            )
        ]
        
        for wh in warehouses:
            session.add(wh)
        session.flush()
        
        print("🏗️ Creating zones and bins...")
        for warehouse in warehouses:
            # Create zones
            zones_data = [
                ("Receiving Area", "receiving", 10),
                ("Storage Area", "storage", 50), 
                ("Picking Zone", "picking", 20),
                ("Shipping Dock", "shipping", 30),
                ("Returns Area", "returns", 40)
            ]
            
            zones = []
            for zone_name, zone_function, priority in zones_data:
                zone = Zone(
                    warehouse_id=warehouse.warehouse_id,
                    zone_name=zone_name,
                    zone_function=zone_function,
                    processing_priority=priority
                )
                session.add(zone)
                zones.append(zone)
            
            session.flush()
            
            # Create bin locations
            for zone in zones:
                bin_count = 5 if zone.zone_function == "storage" else 2
                for i in range(1, bin_count + 1):
                    bin_location = BinLocation(
                        warehouse_id=warehouse.warehouse_id,
                        zone_id=zone.zone_id,
                        bin_location_code=f"{zone.zone_function.upper()}-{i:03d}",
                        bin_location_type="shelf" if zone.zone_function == "storage" else "staging",
                        maximum_weight_kilograms=500.0,
                        is_pick_face=(zone.zone_function == "picking")
                    )
                    session.add(bin_location)
        
        print("📋 Creating item groups...")
        item_groups = [
            ItemGroup(
                item_group_code="ELECTRONICS",
                item_group_name="Electronics & Gadgets",
                handling_policy={"prohibit_mixing_lots": True, "require_serial_tracking": True}
            ),
            ItemGroup(
                item_group_code="CLOTHING",
                item_group_name="Clothing & Apparel", 
                handling_policy={"prohibit_mixing_lots": False, "require_serial_tracking": False}
            ),
            ItemGroup(
                item_group_code="BOOKS",
                item_group_name="Books & Media",
                handling_policy={"prohibit_mixing_lots": False, "require_serial_tracking": False}
            )
        ]
        
        for ig in item_groups:
            session.add(ig)
        session.flush()
        
        print("📱 Creating sample items...")
        for i, item_group in enumerate(item_groups):
            for j in range(1, 4):  # 3 items per group
                item = Item(
                    stock_keeping_unit=f"SKU-{item_group.item_group_code}-{j:03d}",
                    item_name=f"{item_group.item_group_name} Item {j}",
                    unit_of_measure="pieces",
                    barcode_value=f"123456789{i:02d}{j:03d}",
                    gross_weight_kilograms=0.5,
                    is_lot_tracked=item_group.handling_policy.get("prohibit_mixing_lots", False),
                    is_serial_number_tracked=item_group.handling_policy.get("require_serial_tracking", False),
                    item_group_id=item_group.item_group_id,
                    item_status="active"
                )
                session.add(item)
        
        print("👥 Creating users...")
        users = [
            AppUser(
                user_email="admin@warehouse.local",
                user_display_name="System Administrator",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e",  # password: admin123
                is_active=True
            ),
            AppUser(
                user_email="manager@warehouse.local", 
                user_display_name="Warehouse Manager",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e",
                is_active=True
            ),
            AppUser(
                user_email="operator@warehouse.local",
                user_display_name="Warehouse Operator", 
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e",
                is_active=True
            )
        ]
        
        for user in users:
            session.add(user)
        session.flush()
        
        print("🔐 Setting up permissions...")
        # Give admin full access to all warehouses
        admin_user = next(u for u in users if u.user_email == "admin@warehouse.local")
        
        for warehouse in warehouses:
            # Warehouse level access
            grant = WarehouseAccessGrant(
                app_user_id=admin_user.app_user_id,
                warehouse_id=warehouse.warehouse_id,
                scope_type="warehouse",
                scope_entity_identifier=warehouse.warehouse_id,
                can_read=True,
                can_write=True,
                can_approve=True
            )
            session.add(grant)
            
            # Item group access
            for item_group in item_groups:
                grant = WarehouseAccessGrant(
                    app_user_id=admin_user.app_user_id,
                    warehouse_id=warehouse.warehouse_id,
                    scope_type="item_group",
                    scope_entity_identifier=item_group.item_group_id,
                    can_read=True,
                    can_write=True,
                    can_approve=True
                )
                session.add(grant)
        
        session.commit()
        print("✅ Demo data created successfully!")
        
        # Print summary
        print(f"\n📊 Created:")
        print(f"   - {len(warehouses)} warehouses")
        print(f"   - {len(item_groups)} item groups") 
        print(f"   - {len(users)} users")
        print(f"   - Admin user: admin@warehouse.local (password: admin123)")
        
        return True


if __name__ == "__main__":
    try:
        success = create_demo_data()
        if success:
            print("\n🎉 Demo data setup completed!")
            sys.exit(0)
        else:
            print("\n❌ Demo data setup failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)