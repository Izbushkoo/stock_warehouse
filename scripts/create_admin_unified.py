#!/usr/bin/env python3
"""Unified script to create admin user with full permissions."""

import sys
import os
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from warehouse_service.db import session_scope
from warehouse_service.config import get_settings
from warehouse_service.models.unified import AppUser, Permission, ItemGroup, Warehouse
from warehouse_service.auth.permissions_v2 import ResourceType, PermissionLevel, PermissionManager
from warehouse_service.auth.password import hash_password
from sqlmodel import select


def create_admin_user(email: str = None, display_name: str = None, password: str = None, interactive: bool = True):
    """Create admin user with full system permissions."""
    
    # Get user input if not provided
    if interactive:
        if not email:
            email = input("Enter admin email: ").strip()
        if not email:
            print("Email is required")
            return False
            
        if not display_name:
            display_name = input(f"Enter display name (default: {email.split('@')[0]}): ").strip()
        if not display_name:
            display_name = email.split('@')[0]
            
        if not password:
            password = input("Enter password: ").strip()
        if not password:
            print("Password is required")
            return False
    else:
        # Non-interactive mode requires all parameters
        if not all([email, display_name, password]):
            print("Error: email, display_name, and password are required in non-interactive mode")
            return False
    
    with session_scope() as session:
        # Check if system admin already exists
        existing_admin = session.exec(
            select(Permission).where(
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.permission_level == PermissionLevel.OWNER.value,
                Permission.is_active.is_(True)
            )
        ).first()
        
        if existing_admin:
            admin_user = session.get(AppUser, existing_admin.app_user_id)
            print(f"System administrator already exists: {admin_user.user_email}")
            if interactive:
                overwrite = input("Create another system admin? (y/N): ").strip().lower()
                if overwrite != 'y':
                    return True
        
        # Check if user already exists
        existing_user = session.exec(
            select(AppUser).where(AppUser.user_email == email)
        ).first()
        
        if existing_user:
            user = existing_user
            print(f"User {email} already exists, granting system admin permissions...")
        else:
            # Create new user
            user = AppUser(
                user_email=email,
                user_display_name=display_name,
                password_hash=hash_password(password),
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"✅ Created user: {email}")
        
        # Grant system admin permission using PermissionManager
        pm = PermissionManager(session)
        
        # For the first system admin, we need to create the permission directly
        # since PermissionManager.grant_permission requires admin rights
        system_permission = Permission(
            app_user_id=user.app_user_id,
            resource_type=ResourceType.SYSTEM.value,
            resource_id=user.app_user_id,  # Use user's own ID as resource_id for system permissions
            permission_level=PermissionLevel.OWNER.value,
            granted_by=user.app_user_id  # Self-granted for first admin
        )
        
        session.add(system_permission)
        
        # Update existing orphaned data with created_by if they don't have it
        # This is for data that was created before the permission system
        session.execute(text("""
            UPDATE item_group SET created_by = :user_id WHERE created_by IS NULL
        """), {"user_id": str(user.app_user_id)})
        
        session.execute(text("""
            UPDATE warehouse SET created_by = :user_id WHERE created_by IS NULL
        """), {"user_id": str(user.app_user_id)})
        
        session.commit()
        session.refresh(user)
        
        # Verify system admin permissions were granted
        pm = PermissionManager(session)
        is_system_admin = pm.is_system_admin(user.app_user_id)
        
        if is_system_admin:
            print(f"\n🎉 System administrator created successfully!")
            print(f"Email: {email}")
            print(f"Display Name: {display_name}")
            print("✅ System administrator privileges granted")
            print()
            print("Permissions granted:")
            print("• Full system administration access")
            print("• Can create and manage item groups")
            print("• Can create and manage warehouses")
            print("• Can manage user permissions")
            print("• Can access all system resources")
            print()
            print("Next steps:")
            print("1. Login to the web interface")
            print("2. Create item groups in the admin panel")
            print("3. Create warehouses and assign them to item groups")
            print("4. Create additional users and assign permissions")
        else:
            print(f"\n❌ Error: Failed to grant system administrator privileges!")
            print("Please check the database and try again.")
            return False
        
        # Show appropriate URLs based on environment
        settings = get_settings()
        if settings.environment == "development":
            print(f"\n🌐 Login at: http://localhost:8000/login")
            print(f"📊 Admin dashboard: http://localhost:8000/admin/")
            print(f"🔐 Permissions: http://localhost:8000/admin/permissions/")
        else:
            print(f"\n🌐 Login at your application URL")
            print(f"📊 Check the admin dashboard for management tools")
        
        return True


def list_system_admins():
    """List all existing system administrators."""
    with session_scope() as session:
        pm = PermissionManager(session)
        
        # Get all system admin permissions
        system_admins = session.exec(
            select(Permission, AppUser).join(AppUser).where(
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.permission_level.in_([PermissionLevel.ADMIN.value, PermissionLevel.OWNER.value]),
                Permission.is_active.is_(True)
            )
        ).all()
        
        if not system_admins:
            print("No system administrators found.")
            return
        
        print("Current system administrators:")
        print("=" * 50)
        for perm, user in system_admins:
            print(f"• {user.user_email} ({user.user_display_name})")
            print(f"  Permission Level: {perm.permission_level}")
            print(f"  Granted: {perm.granted_at}")
            print(f"  Active: {'Yes' if user.is_active else 'No'}")
            print()


def main():
    """Main function."""
    if len(sys.argv) == 1:
        # Interactive mode
        print("Creating system administrator (interactive mode)")
        print("=" * 50)
        create_admin_user()
    elif len(sys.argv) == 2 and sys.argv[1] == "--list":
        # List existing admins
        list_system_admins()
    elif len(sys.argv) == 4:
        # Non-interactive mode
        email = sys.argv[1]
        display_name = sys.argv[2]
        password = sys.argv[3]
        
        print(f"Creating admin user (non-interactive mode)...")
        print(f"Email: {email}")
        print(f"Display Name: {display_name}")
        print(f"Password: {'*' * len(password)}")
        print()
        
        success = create_admin_user(email, display_name, password, interactive=False)
        if not success:
            sys.exit(1)
    else:
        print("Usage:")
        print("  Interactive mode:     python create_admin_unified.py")
        print("  Non-interactive:      python create_admin_unified.py <email> <display_name> <password>")
        print("  List existing admins: python create_admin_unified.py --list")
        print()
        print("Examples:")
        print("  python create_admin_unified.py")
        print("  python create_admin_unified.py admin@warehouse.local 'Admin User' admin123")
        print("  python create_admin_unified.py --list")
        sys.exit(1)


if __name__ == "__main__":
    main()