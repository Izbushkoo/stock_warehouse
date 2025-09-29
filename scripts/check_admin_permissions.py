#!/usr/bin/env python3
"""Script to check admin permissions for debugging."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from warehouse_service.db import session_scope
from warehouse_service.models.unified import AppUser, Permission
from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType, PermissionLevel
from sqlmodel import select


def check_user_permissions(email: str):
    """Check permissions for a specific user."""
    with session_scope() as session:
        # Find user
        user = session.exec(
            select(AppUser).where(AppUser.user_email == email)
        ).first()
        
        if not user:
            print(f"❌ User {email} not found")
            return
        
        print(f"👤 User: {user.user_email} ({user.user_display_name})")
        print(f"   Active: {user.is_active}")
        print(f"   User ID: {user.app_user_id}")
        print()
        
        # Check system admin status
        pm = PermissionManager(session)
        is_admin = pm.is_system_admin(user.app_user_id)
        print(f"🔐 System Admin Status: {'✅ YES' if is_admin else '❌ NO'}")
        print()
        
        # Get all permissions
        permissions = session.exec(
            select(Permission).where(
                Permission.app_user_id == user.app_user_id,
                Permission.is_active.is_(True)
            )
        ).all()
        
        if not permissions:
            print("❌ No active permissions found")
            return
        
        print("📋 Active Permissions:")
        print("-" * 50)
        for perm in permissions:
            print(f"Resource Type: {perm.resource_type}")
            print(f"Resource ID: {perm.resource_id}")
            print(f"Permission Level: {perm.permission_level}")
            print(f"Granted At: {perm.granted_at}")
            print(f"Expires At: {perm.expires_at or 'Never'}")
            print(f"Granted By: {perm.granted_by}")
            print("-" * 30)
        
        # Check specific system permissions
        system_perms = session.exec(
            select(Permission).where(
                Permission.app_user_id == user.app_user_id,
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.is_active.is_(True)
            )
        ).all()
        
        print(f"\n🏛️ System Permissions: {len(system_perms)} found")
        for perm in system_perms:
            print(f"   Level: {perm.permission_level}")
            print(f"   Resource ID: {perm.resource_id}")
            print(f"   Active: {perm.is_active}")


def list_all_system_admins():
    """List all system administrators."""
    with session_scope() as session:
        system_admins = session.exec(
            select(Permission, AppUser).join(AppUser).where(
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.permission_level.in_([PermissionLevel.ADMIN.value, PermissionLevel.OWNER.value]),
                Permission.is_active.is_(True)
            )
        ).all()
        
        print("🏛️ All System Administrators:")
        print("=" * 50)
        
        if not system_admins:
            print("❌ No system administrators found!")
            return
        
        for perm, user in system_admins:
            print(f"👤 {user.user_email} ({user.user_display_name})")
            print(f"   Level: {perm.permission_level}")
            print(f"   Active: {'✅' if user.is_active else '❌'}")
            print(f"   User ID: {user.app_user_id}")
            print()


def main():
    """Main function."""
    if len(sys.argv) == 2:
        email = sys.argv[1]
        check_user_permissions(email)
    elif len(sys.argv) == 1:
        list_all_system_admins()
    else:
        print("Usage:")
        print("  List all admins: python check_admin_permissions.py")
        print("  Check specific user: python check_admin_permissions.py <email>")
        print()
        print("Examples:")
        print("  python check_admin_permissions.py")
        print("  python check_admin_permissions.py admin@warehouse.local")


if __name__ == "__main__":
    main()