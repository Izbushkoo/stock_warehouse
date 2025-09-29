"""Permission utilities for checking user roles and access."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from warehouse_service.models.unified import AppUser, WarehouseAccessGrant


def is_admin(user: AppUser, session: Session) -> bool:
    """Check if user has admin privileges (can_approve permission)."""
    if not user or not user.is_active:
        return False
    
    has_admin_permission = session.exec(
        select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user.app_user_id,
            WarehouseAccessGrant.can_approve.is_(True),
        )
    ).first()
    
    return has_admin_permission is not None


def can_manage_users(user: AppUser, session: Session) -> bool:
    """Check if user can manage other users (same as is_admin for now)."""
    return is_admin(user, session)


def get_user_permissions_summary(user: AppUser, session: Session) -> dict:
    """Get summary of user's permissions across all warehouses."""
    if not user:
        return {
            "is_admin": False,
            "can_manage_users": False,
            "warehouses": [],
            "total_grants": 0
        }
    
    grants = session.exec(
        select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user.app_user_id
        )
    ).all()
    
    is_user_admin = any(grant.can_approve for grant in grants)
    
    warehouse_permissions = {}
    for grant in grants:
        warehouse_id = str(grant.warehouse_id)
        if warehouse_id not in warehouse_permissions:
            warehouse_permissions[warehouse_id] = {
                "can_read": False,
                "can_write": False,
                "can_approve": False
            }
        
        if grant.can_read:
            warehouse_permissions[warehouse_id]["can_read"] = True
        if grant.can_write:
            warehouse_permissions[warehouse_id]["can_write"] = True
        if grant.can_approve:
            warehouse_permissions[warehouse_id]["can_approve"] = True
    
    return {
        "is_admin": is_user_admin,
        "can_manage_users": is_user_admin,
        "warehouses": warehouse_permissions,
        "total_grants": len(grants)
    }


def require_admin(user: AppUser, session: Session) -> None:
    """Raise exception if user is not admin."""
    from fastapi import HTTPException, status
    
    if not is_admin(user, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )


def require_warehouse_access(
    user: AppUser, 
    session: Session, 
    warehouse_id: UUID, 
    permission: str = "read"
) -> None:
    """Raise exception if user doesn't have warehouse access."""
    from fastapi import HTTPException, status
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Admins have access to everything
    if is_admin(user, session):
        return
    
    # Check specific warehouse permission
    permission_field = f"can_{permission}"
    
    grant = session.exec(
        select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user.app_user_id,
            WarehouseAccessGrant.warehouse_id == warehouse_id,
            getattr(WarehouseAccessGrant, permission_field).is_(True)
        )
    ).first()
    
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for warehouse {warehouse_id}"
        )