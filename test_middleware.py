#!/usr/bin/env python3
"""Simple test script for middleware functionality."""

import asyncio
import json
from uuid import uuid4

import httpx

BASE_URL = "http://localhost:8000"

async def test_middleware():
    """Test middleware authentication and authorization."""
    
    async with httpx.AsyncClient() as client:
        # Test public endpoint (should work without auth)
        response = await client.get(f"{BASE_URL}/api/status")
        print(f"Public endpoint status: {response.status_code}")
        
        # Test protected endpoint without auth (should fail)
        response = await client.get(f"{BASE_URL}/api/v1/warehouses")
        print(f"Protected endpoint without auth: {response.status_code}")
        
        # Test login
        login_data = {
            "email": "admin@example.com",
            "password": "admin123"
        }
        response = await client.post(f"{BASE_URL}/api/auth/login", json=login_data)
        print(f"Login status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                
                # Test protected endpoint with auth (should work)
                response = await client.get(f"{BASE_URL}/api/v1/warehouses", headers=headers)
                print(f"Protected endpoint with auth: {response.status_code}")
                
                # Test warehouse-specific endpoint
                if response.status_code == 200:
                    warehouses = response.json()
                    if warehouses:
                        warehouse_id = warehouses[0]["warehouse_id"]
                        response = await client.get(
                            f"{BASE_URL}/api/v1/warehouses/{warehouse_id}/stock-balance",
                            headers=headers
                        )
                        print(f"Warehouse stock balance: {response.status_code}")
                
                # Test POST endpoint with warehouse_id in body
                stock_movement_data = {
                    "warehouse_id": str(uuid4()),
                    "item_id": str(uuid4()),
                    "moved_quantity": 10.0,
                    "movement_reason": "test"
                }
                response = await client.post(
                    f"{BASE_URL}/api/v1/stock-movements",
                    json=stock_movement_data,
                    headers=headers
                )
                print(f"Stock movement creation: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_middleware())