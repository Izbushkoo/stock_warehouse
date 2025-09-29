#!/usr/bin/env python3
"""Debug authentication and permissions."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from warehouse_service.db import session_scope
from warehouse_service.models.unified import AppUser, Permission
from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType, PermissionLevel
from warehouse_service.auth.auth_service import AuthService
from sqlmodel import select


def test_auth_flow(email: str, password: str):
    """Test complete authentication flow."""
    print(f"🔍 Testing authentication flow for: {email}")
    print("=" * 60)
    
    with session_scope() as session:
        auth_service = AuthService(session)
        
        # Step 1: Authenticate user
        print("1️⃣ Testing user authentication...")
        user = auth_service.authenticate_user(email, password)
        if not user:
            print("❌ Authentication failed - invalid email or password")
            return
        
        print(f"✅ User authenticated: {user.user_email}")
        print(f"   User ID: {user.app_user_id}")
        print(f"   Active: {user.is_active}")
        print()
        
        # Step 2: Generate token
        print("2️⃣ Testing token generation...")
        try:
            token_response = auth_service.login_user(email, password)
            if not token_response:
                print("❌ Token generation failed")
                return
            
            token = token_response.access_token
            print(f"✅ Token generated: {token[:20]}...")
            print()
        except Exception as e:
            print(f"❌ Token generation error: {e}")
            return
        
        # Step 3: Verify token
        print("3️⃣ Testing token verification...")
        try:
            user_from_token = auth_service.get_user_by_token(token)
            if not user_from_token:
                print("❌ Token verification failed")
                return
            
            print(f"✅ Token verified, user: {user_from_token.user_email}")
            print(f"   Same user: {'✅' if user.app_user_id == user_from_token.app_user_id else '❌'}")
            print()
        except Exception as e:
            print(f"❌ Token verification error: {e}")
            return
        
        # Step 4: Check system admin permissions
        print("4️⃣ Testing system admin permissions...")
        pm = PermissionManager(session)
        is_admin = pm.is_system_admin(user.app_user_id)
        print(f"System Admin Status: {'✅ YES' if is_admin else '❌ NO'}")
        
        if not is_admin:
            print("\n🔍 Checking why user is not system admin...")
            
            # Check all permissions
            all_perms = session.exec(
                select(Permission).where(
                    Permission.app_user_id == user.app_user_id
                )
            ).all()
            
            print(f"Total permissions found: {len(all_perms)}")
            
            for perm in all_perms:
                print(f"  - Type: {perm.resource_type}, Level: {perm.permission_level}, Active: {perm.is_active}")
            
            # Check system permissions specifically
            system_perms = session.exec(
                select(Permission).where(
                    Permission.app_user_id == user.app_user_id,
                    Permission.resource_type == ResourceType.SYSTEM.value
                )
            ).all()
            
            print(f"\nSystem permissions found: {len(system_perms)}")
            for perm in system_perms:
                print(f"  - Level: {perm.permission_level}")
                print(f"  - Active: {perm.is_active}")
                print(f"  - Expires: {perm.expires_at or 'Never'}")
                print(f"  - Required levels: {[PermissionLevel.ADMIN.value, PermissionLevel.OWNER.value]}")
                print(f"  - Level matches: {perm.permission_level in [PermissionLevel.ADMIN.value, PermissionLevel.OWNER.value]}")
        
        print()
        
        # Step 5: Test require_system_admin function
        print("5️⃣ Testing require_system_admin function...")
        try:
            from warehouse_service.auth.permissions_v2 import require_system_admin
            require_system_admin(user, session)
            print("✅ require_system_admin passed")
        except Exception as e:
            print(f"❌ require_system_admin failed: {e}")


def main():
    """Main function."""
    if len(sys.argv) != 3:
        print("Usage: python debug_auth.py <email> <password>")
        print("Example: python debug_auth.py admin@warehouse.local admin123")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    test_auth_flow(email, password)


if __name__ == "__main__":
    main()