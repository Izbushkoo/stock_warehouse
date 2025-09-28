#!/usr/bin/env python3
"""Quick system status check script."""

import sys
import os
from sqlalchemy import text

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from warehouse_service.db import session_scope


def check_system_status():
    """Check if the unified warehouse system is properly set up."""
    print("🔍 Checking unified warehouse system status...")
    
    try:
        with session_scope() as session:
            # Check if main tables exist and have data
            tables_to_check = [
                ('warehouse', 'Warehouses'),
                ('zone', 'Zones'),
                ('bin_location', 'Bin Locations'),
                ('item_group', 'Item Groups'),
                ('item', 'Items'),
                ('app_user', 'Users'),
                ('warehouse_access_grant', 'Access Grants'),
            ]
            
            print("\n📊 Database Tables Status:")
            for table_name, display_name in tables_to_check:
                try:
                    result = session.exec(text(f"SELECT COUNT(*) FROM {table_name}")).first()
                    count = result if result is not None else 0
                    status = "✅" if count > 0 else "⚠️"
                    print(f"   {status} {display_name}: {count} records")
                except Exception as e:
                    print(f"   ❌ {display_name}: Error - {str(e)}")
            
            # Check if triggers exist
            print("\n🔧 Database Triggers Status:")
            trigger_check = session.exec(text("""
                SELECT trigger_name, event_object_table 
                FROM information_schema.triggers 
                WHERE trigger_schema = 'public'
                ORDER BY event_object_table, trigger_name
            """)).all()
            
            if trigger_check:
                for trigger in trigger_check:
                    print(f"   ✅ {trigger.trigger_name} on {trigger.event_object_table}")
            else:
                print("   ⚠️ No triggers found")
            
            # Check if functions exist
            print("\n⚙️ Database Functions Status:")
            function_check = session.exec(text("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'public' 
                AND routine_type = 'FUNCTION'
                ORDER BY routine_name
            """)).all()
            
            if function_check:
                for func in function_check:
                    print(f"   ✅ {func.routine_name}()")
            else:
                print("   ⚠️ No custom functions found")
            
            # Test basic functionality
            print("\n🧪 Basic Functionality Test:")
            
            # Check if we can query warehouses
            warehouses = session.exec(text("SELECT warehouse_code, warehouse_name FROM warehouse LIMIT 3")).all()
            if warehouses:
                print("   ✅ Can query warehouses:")
                for wh in warehouses:
                    print(f"      - {wh.warehouse_code}: {wh.warehouse_name}")
            else:
                print("   ⚠️ No warehouses found")
            
            # Check if we can query users
            users = session.exec(text("SELECT user_email, user_display_name FROM app_user LIMIT 3")).all()
            if users:
                print("   ✅ Can query users:")
                for user in users:
                    print(f"      - {user.user_email}: {user.user_display_name}")
            else:
                print("   ⚠️ No users found")
            
            # Check if we can query items
            items = session.exec(text("SELECT stock_keeping_unit, item_name FROM item LIMIT 5")).all()
            if items:
                print("   ✅ Can query items:")
                for item in items:
                    print(f"      - {item.stock_keeping_unit}: {item.item_name}")
            else:
                print("   ⚠️ No items found")
            
            print("\n🎉 System status check completed!")
            return True
            
    except Exception as e:
        print(f"\n❌ System check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = check_system_status()
        if success:
            print("\n✅ Unified warehouse system appears to be working correctly!")
            sys.exit(0)
        else:
            print("\n❌ System check failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)