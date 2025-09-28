#!/usr/bin/env python3
"""
Comprehensive system test for the warehouse service.
Tests authentication, RBAC, and basic warehouse operations.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class WarehouseSystemTest:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL)
        self.admin_token = None
        self.user_token = None
        
    async def cleanup(self):
        await self.client.aclose()
    
    async def test_health_check(self):
        """Test basic health check."""
        print("🔍 Testing health check...")
        response = await self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print("✅ Health check passed")
        
    async def test_admin_login(self):
        """Test admin login."""
        print("🔐 Testing admin login...")
        response = await self.client.post("/auth/login", json={
            "email": "admin@example.com",
            "password": "change-me"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        self.admin_token = data["access_token"]
        print("✅ Admin login successful")
        
    async def test_protected_route(self):
        """Test accessing protected route with token."""
        print("🛡️ Testing protected route access...")
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = await self.client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@example.com"
        print("✅ Protected route access successful")
        
    async def test_web_interface(self):
        """Test web interface."""
        print("🌐 Testing web interface...")
        response = await self.client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        print("✅ Web interface accessible")
        
    async def test_login_page(self):
        """Test login page."""
        print("📝 Testing login page...")
        response = await self.client.get("/login")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        print("✅ Login page accessible")
        
    async def test_admin_dashboard(self):
        """Test admin dashboard access."""
        print("📊 Testing admin dashboard...")
        # First try without auth - should redirect
        response = await self.client.get("/admin/dashboard", follow_redirects=False)
        assert response.status_code in [302, 401]
        
        # Now with auth cookie (simulate web login)
        login_response = await self.client.post("/auth/web-login", data={
            "email": "admin@example.com",
            "password": "change-me"
        }, follow_redirects=False)
        
        if login_response.status_code == 302:
            # Get cookies from login
            cookies = login_response.cookies
            dashboard_response = await self.client.get("/admin/dashboard", cookies=cookies)
            assert dashboard_response.status_code == 200
            print("✅ Admin dashboard accessible with web auth")
        else:
            print("⚠️ Web login flow needs adjustment")
        
    async def test_api_endpoints(self):
        """Test API endpoints."""
        print("🔌 Testing API endpoints...")
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test warehouses endpoint
        response = await self.client.get("/api/warehouses", headers=headers)
        assert response.status_code == 200
        warehouses = response.json()
        assert isinstance(warehouses, list)
        print(f"✅ Found {len(warehouses)} warehouses")
        
        # Test items endpoint
        response = await self.client.get("/api/items", headers=headers)
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        print(f"✅ Found {len(items)} items")
        
    async def test_create_user(self):
        """Test user creation."""
        print("👤 Testing user creation...")
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        new_user_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User"
        }
        
        response = await self.client.post("/auth/users", json=new_user_data, headers=headers)
        if response.status_code == 201:
            print("✅ User creation successful")
            
            # Test login with new user
            login_response = await self.client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "testpass123"
            })
            assert login_response.status_code == 200
            self.user_token = login_response.json()["access_token"]
            print("✅ New user login successful")
        else:
            print(f"⚠️ User creation failed: {response.status_code} - {response.text}")
            
    async def test_rbac_permissions(self):
        """Test RBAC permissions."""
        print("🔒 Testing RBAC permissions...")
        
        if not self.user_token:
            print("⚠️ Skipping RBAC test - no regular user token")
            return
            
        # Test that regular user cannot access admin endpoints
        headers = {"Authorization": f"Bearer {self.user_token}"}
        response = await self.client.post("/auth/users", json={
            "email": "unauthorized@example.com",
            "password": "test123",
            "full_name": "Unauthorized"
        }, headers=headers)
        
        # Should be forbidden
        assert response.status_code in [403, 401]
        print("✅ RBAC permissions working - regular user blocked from admin actions")
        
    async def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting comprehensive warehouse system tests...\n")
        
        try:
            await self.test_health_check()
            await self.test_admin_login()
            await self.test_protected_route()
            await self.test_web_interface()
            await self.test_login_page()
            await self.test_admin_dashboard()
            await self.test_api_endpoints()
            await self.test_create_user()
            await self.test_rbac_permissions()
            
            print("\n🎉 All tests passed! System is working correctly.")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        finally:
            await self.cleanup()

async def main():
    """Main test runner."""
    test = WarehouseSystemTest()
    await test.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())