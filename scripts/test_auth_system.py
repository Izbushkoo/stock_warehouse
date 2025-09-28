#!/usr/bin/env python3
"""Test authentication system."""

import sys
import os
import asyncio
import httpx

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


async def test_auth_system():
    """Test the authentication system."""
    print("🔐 Testing authentication system...")
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test registration
            print("\n📝 Testing user registration...")
            register_data = {
                "email": "test@warehouse.local",
                "display_name": "Test User",
                "password": "test123",
                "is_active": True
            }
            
            response = await client.post(f"{base_url}/api/auth/register", json=register_data)
            if response.status_code == 200:
                user_data = response.json()
                print(f"   ✅ User registered: {user_data['email']}")
            elif response.status_code == 400 and "already exists" in response.text:
                print("   ⚠️ User already exists, continuing...")
            else:
                print(f"   ❌ Registration failed: {response.status_code} - {response.text}")
                return False
            
            # Test login
            print("\n🔑 Testing login...")
            login_data = {
                "email": "admin@warehouse.local",
                "password": "admin123"
            }
            
            response = await client.post(f"{base_url}/api/auth/login", json=login_data)
            if response.status_code == 200:
                token_data = response.json()
                print(f"   ✅ Login successful")
                print(f"   🎫 Token type: {token_data['token_type']}")
                print(f"   ⏰ Expires in: {token_data['expires_in']} seconds")
                
                access_token = token_data["access_token"]
            else:
                print(f"   ❌ Login failed: {response.status_code} - {response.text}")
                return False
            
            # Test authenticated endpoint
            print("\n👤 Testing authenticated endpoint...")
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = await client.get(f"{base_url}/api/auth/me", headers=headers)
            if response.status_code == 200:
                user_info = response.json()
                print(f"   ✅ User info retrieved:")
                print(f"      - Email: {user_info['email']}")
                print(f"      - Name: {user_info['display_name']}")
                print(f"      - Active: {user_info['is_active']}")
            else:
                print(f"   ❌ User info failed: {response.status_code} - {response.text}")
                return False
            
            # Test permissions
            print("\n🔐 Testing user permissions...")
            response = await client.get(f"{base_url}/api/auth/permissions", headers=headers)
            if response.status_code == 200:
                permissions = response.json()
                print(f"   ✅ Permissions retrieved:")
                print(f"      - User ID: {permissions['user_id']}")
                print(f"      - Warehouses: {len(permissions['permissions']['warehouses'])}")
            else:
                print(f"   ❌ Permissions failed: {response.status_code} - {response.text}")
            
            # Test warehouses endpoint with auth
            print("\n🏭 Testing warehouses endpoint with auth...")
            response = await client.get(f"{base_url}/api/v1/warehouses", headers=headers)
            if response.status_code == 200:
                warehouses = response.json()
                print(f"   ✅ Warehouses retrieved: {len(warehouses)} warehouses")
                for wh in warehouses[:2]:
                    print(f"      - {wh['warehouse_code']}: {wh['warehouse_name']}")
            else:
                print(f"   ❌ Warehouses failed: {response.status_code} - {response.text}")
            
            # Test without auth
            print("\n🚫 Testing endpoint without auth...")
            response = await client.get(f"{base_url}/api/v1/warehouses")
            if response.status_code == 401:
                print("   ✅ Correctly rejected unauthenticated request")
            else:
                print(f"   ⚠️ Expected 401, got {response.status_code}")
            
            print("\n🎉 Authentication system test completed!")
            return True
            
        except httpx.ConnectError:
            print("❌ Could not connect to server. Make sure it's running on http://localhost:8000")
            return False
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_auth_system())
        if success:
            print("\n✅ Authentication system is working!")
            print("\n🌐 Try the web interface:")
            print("   - Login page: http://localhost:8000/")
            print("   - Admin panel: http://localhost:8000/admin")
            print("   - API docs: http://localhost:8000/docs")
            sys.exit(0)
        else:
            print("\n❌ Authentication tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)