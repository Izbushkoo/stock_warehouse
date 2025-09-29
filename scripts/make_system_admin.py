#!/usr/bin/env python3
"""Script to make a user system administrator."""

import sys
from uuid import UUID
from sqlmodel import Session, select

from warehouse_service.database import get_engine
from warehouse_service.models.unified import AppUser, Permission
from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType, PermissionLevel


def make_system_admin(user_email: str):
    """Make user system administrator."""
    engine = get_engine()
    
    with Session(engine) as session:
        # Find user by email
        user = session.exec(
            select(AppUser).where(AppUser.user_email == user_email)
        ).first()
        
        if not user:
            print(f"❌ User with email '{user_email}' not found")
            return False
        
        pm = PermissionManager(session)
        
        # Check if already system admin
        if pm.is_system_admin(user.app_user_id):
            print(f"✅ User '{user_email}' is already system administrator")
            return True
        
        # Create system permission
        permission = Permission(
            app_user_id=user.app_user_id,
            resource_type=ResourceType.SYSTEM.value,
            resource_id=user.app_user_id,  # Use user's own ID as resource_id for system permissions
            permission_level=PermissionLevel.ADMIN.value,
            granted_by=user.app_user_id,  # Self-granted for first admin
            is_active=True
        )
        
        session.add(permission)
        session.commit()
        
        print(f"✅ User '{user_email}' is now system administrator")
        return True


def list_system_admins():
    """List all system administrators."""
    engine = get_engine()
    
    with Session(engine) as session:
        # Get all system permissions
        system_permissions = session.exec(
            select(Permission, AppUser).join(AppUser).where(
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.permission_level.in_([PermissionLevel.ADMIN.value, PermissionLevel.OWNER.value]),
                Permission.is_active.is_(True)
            )
        ).all()
        
        if not system_permissions:
            print("❌ No system administrators found")
            return
        
        print("📋 System Administrators:")
        for perm, user in system_permissions:
            print(f"  - {user.user_email} ({user.user_display_name}) - {perm.permission_level}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/make_system_admin.py <user_email>  # Make user system admin")
        print("  python scripts/make_system_admin.py --list        # List system admins")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_system_admins()
    else:
        user_email = sys.argv[1]
        make_system_admin(user_email)


if __name__ == "__main__":
    main()