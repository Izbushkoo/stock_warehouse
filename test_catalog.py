#!/usr/bin/env python3
"""Test script to verify catalog functionality."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_catalog():
    """Test catalog endpoints."""
    
    # First, try to access catalog without authentication
    print("Testing catalog access without authentication...")
    response = requests.get(f"{BASE_URL}/catalog")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 302:
        print("✓ Correctly redirected to login when not authenticated")
    else:
        print("✗ Expected redirect to login")
    
    # Test with authentication (you'll need to get a token first)
    print("\nTo test with authentication, you need to:")
    print("1. Login via the web interface or API")
    print("2. Get an access token")
    print("3. Use the token to access /catalog")
    
    print(f"\nCatalog URL: {BASE_URL}/catalog")

if __name__ == "__main__":
    test_catalog()