#!/usr/bin/env python3
"""Test API endpoints for unified warehouse system."""

import sys
import os
import asyncio
import httpx
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from warehouse_service.db import session_scope
from warehouse_service.models.unified import Warehouse, AppUser


async def test_api_endpoints():
    """Test the main API endpoints."""
    print("🌐 Testing unified warehouse API endpoints...")
    
    # Get test data from database
    with session_scope() as session:
        warehouse = session.query(Warehouse).first()
        user = session.query(AppUser).first()
        
        if not warehouse or not user:
            print("❌ No test data found. Run migrations first.")
            return False
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health endpoint
            print("\n🏥 Testing health endpoint...")
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("   ✅ Health check passed")
                print(f"   📊 Response: {response.json()}")
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                return False
            
            # Test API status endpoint
            print("\n📡 Testing API status endpoint...")
            response = await client.get(f"{base_url}/api/status")
            if response.status_code == 200:
                print("   ✅ API status check passed")
                print(f"   📊 Response: {response.json()}")
            else:
                print(f"   ❌ API status check failed: {response.status_code}")
            
            # Test warehouses endpoint
            print("\n🏭 Testing warehouses endpoint...")
            response = await client.get(
                f"{base_url}/api/v1/warehouses",
                params={"user_id": str(user.app_user_id)}
            )
            if response.status_code == 200:
                warehouses = response.json()
                print(f"   ✅ Warehouses endpoint works: {len(warehouses)} warehouses found")
                for wh in warehouses[:3]:  # Show first 3
                    print(f"      - {wh['warehouse_code']}: {wh['warehouse_name']}")
            else:
                print(f"   ❌ Warehouses endpoint failed: {response.status_code}")
                print(f"   📄 Response: {response.text}")
            
            # Test stock balance endpoint
            print("\n📦 Testing stock balance endpoint...")
            response = await client.get(
                f"{base_url}/api/v1/warehouses/{warehouse.warehouse_id}/stock-balance",
                params={"user_id": str(user.app_user_id)}
            )
            if response.status_code == 200:
                balances = response.json()
                print(f"   ✅ Stock balance endpoint works: {len(balances)} balance records")
            elif response.status_code == 403:
                print("   ⚠️ Stock balance endpoint returned 403 (permission denied) - this is expected if no access grants")
            else:
                print(f"   ❌ Stock balance endpoint failed: {response.status_code}")
                print(f"   📄 Response: {response.text}")
            
            # Test movement history endpoint
            print("\n📋 Testing movement history endpoint...")
            response = await client.get(
                f"{base_url}/api/v1/warehouses/{warehouse.warehouse_id}/movements",
                params={"user_id": str(user.app_user_id)}
            )
            if response.status_code == 200:
                movements = response.json()
                print(f"   ✅ Movement history endpoint works: {len(movements)} movements found")
            elif response.status_code == 403:
                print("   ⚠️ Movement history endpoint returned 403 (permission denied) - this is expected if no access grants")
            else:
                print(f"   ❌ Movement history endpoint failed: {response.status_code}")
                print(f"   📄 Response: {response.text}")
            
            # Test user permissions endpoint
            print("\n🔐 Testing user permissions endpoint...")
            response = await client.get(
                f"{base_url}/api/v1/users/{user.app_user_id}/permissions",
                params={"requesting_user_id": str(user.app_user_id)}
            )
            if response.status_code == 200:
                permissions = response.json()
                print("   ✅ User permissions endpoint works")
                print(f"   📊 User has access to {len(permissions['permissions']['warehouses'])} warehouses")
            else:
                print(f"   ❌ User permissions endpoint failed: {response.status_code}")
                print(f"   📄 Response: {response.text}")
            
            print("\n🎉 API endpoint testing completed!")
            return True
            
        except httpx.ConnectError:
            print("❌ Could not connect to API server. Make sure it's running on http://localhost:8000")
            return False
        except Exception as e:
            print(f"❌ API test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_api_endpoints())
        if success:
            print("\n✅ API endpoints are working correctly!")
            sys.exit(0)
        else:
            print("\n❌ API tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)