"""API routes for user lifecycle management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from warehouse_service.auth.auth_service import AuthService
from warehouse_service.auth.dependencies import get_current_user, require_system_admin, get_session
from warehouse_service.models.unified import AppUser
from warehouse_service.auth.user_lifecycle import UserLifecycleService
from warehouse_service.auth.permissions_v2 import PermissionManager
from warehouse_service.tasks.user_cleanup import (
    deactivate_user_with_resources,
    reactivate_user_with_resources,
    cleanup_old_deleted_users
)

router = APIRouter(prefix="/api/users", tags=["User Management"])


class UpdateUserStatusRequest(BaseModel):
    """Request to update user status."""
    is_active: bool


class UpdateUserRequest(BaseModel):
    """Request to update user information."""
    display_name: Optional[str] = None
    email: Optional[str] = None


class UpdatePermissionsRequest(BaseModel):
    """Request to update user permissions."""
    permissions: dict


class DeactivateUserRequest(BaseModel):
    """Request to deactivate a user."""
    user_id: UUID
    reason: Optional[str] = None


class ReactivateUserRequest(BaseModel):
    """Request to reactivate a user."""
    user_id: UUID


class UserResponse(BaseModel):
    """User response model."""
    app_user_id: str
    user_email: str
    user_display_name: str
    is_active: bool
    created_at: str
    last_login_at: Optional[str]


@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """List all users. Only system admins can access this."""
    from sqlmodel import select
    
    users = session.exec(select(AppUser)).all()
    
    return [
        UserResponse(
            app_user_id=str(user.app_user_id),
            user_email=user.user_email,
            user_display_name=user.user_display_name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None
        )
        for user in users
    ]


class UserLifecycleResponse(BaseModel):
    """Response for user lifecycle operations."""
    success: bool
    message: str
    user_id: UUID


class CleanupResponse(BaseModel):
    """Response for cleanup operations."""
    success: bool
    message: str
    deleted_count: Optional[int] = None


@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    request: UpdateUserStatusRequest,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """Update user active status (simple toggle)."""
    auth_service = AuthService(session)
    
    try:
        updated_user = auth_service.update_user_status(str(user_id), request.is_active)
        return auth_service.get_user_response(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/{user_id}")
async def update_user_info(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """Update user information."""
    auth_service = AuthService(session)
    
    user_data = {}
    if request.display_name is not None:
        user_data['display_name'] = request.display_name
    if request.email is not None:
        user_data['email'] = request.email
    
    try:
        updated_user = auth_service.update_user(str(user_id), user_data)
        return auth_service.get_user_response(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/{user_id}/permissions")
async def update_user_permissions(
    user_id: UUID,
    request: UpdatePermissionsRequest,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """Update user permissions."""
    auth_service = AuthService(session)
    
    try:
        # Передаем ID текущего пользователя как того, кто выдает разрешения
        updated_user = auth_service.update_user_permissions_with_granter(
            str(user_id), 
            request.permissions, 
            current_user.app_user_id
        )
        return auth_service.get_user_response(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: UUID,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """Delete user permanently."""
    # Prevent self-deletion
    if user_id == current_user.app_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    auth_service = AuthService(session)
    
    try:
        auth_service.delete_user(str(user_id))
        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/deactivate", response_model=UserLifecycleResponse)
async def deactivate_user(
    request: DeactivateUserRequest,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """
    Deactivate user and soft delete all their created resources.
    Requires system admin privileges.
    """
    auth_service = AuthService(session)
    
    # Check if target user exists
    target_user = session.get(AppUser, request.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deactivation
    if target_user.app_user_id == current_user.app_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Deactivate user and soft delete resources
    success = auth_service.deactivate_user_cascade(
        request.user_id, 
        current_user.app_user_id, 
        request.reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )
    
    return UserLifecycleResponse(
        success=True,
        message=f"User {target_user.user_email} has been deactivated and their resources soft deleted",
        user_id=request.user_id
    )


@router.post("/reactivate", response_model=UserLifecycleResponse)
async def reactivate_user(
    request: ReactivateUserRequest,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """
    Reactivate user and restore all their soft deleted resources.
    Requires system admin privileges.
    """
    auth_service = AuthService(session)
    
    # Check if target user exists
    target_user = session.get(AppUser, request.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Reactivate user and restore resources
    success = auth_service.reactivate_user_cascade(
        request.user_id, 
        current_user.app_user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate user"
        )
    
    return UserLifecycleResponse(
        success=True,
        message=f"User {target_user.user_email} has been reactivated and their resources restored",
        user_id=request.user_id
    )


@router.get("/pending-deletion", response_model=List[dict])
async def get_users_pending_deletion(
    days_threshold: int = 30,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """
    Get list of users eligible for permanent deletion.
    Requires system admin privileges.
    """
    auth_service = AuthService(session)
    
    eligible_users = auth_service.get_users_for_permanent_deletion(days_threshold)
    
    return [
        {
            "user_id": str(user.app_user_id),
            "email": user.user_email,
            "display_name": user.user_display_name,
            "is_active": user.is_active,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }
        for user in eligible_users
    ]


@router.post("/cleanup", response_model=CleanupResponse)
async def trigger_cleanup(
    days_threshold: int = 30,
    current_user: AppUser = Depends(require_system_admin)
):
    """
    Trigger immediate cleanup of old soft deleted users and resources.
    Requires system admin privileges.
    """
    # Trigger Celery task for cleanup
    task = cleanup_old_deleted_users.delay(days_threshold)
    
    return CleanupResponse(
        success=True,
        message=f"Cleanup task triggered for users deleted more than {days_threshold} days ago. Task ID: {task.id}"
    )


@router.post("/deactivate-async", response_model=dict)
async def deactivate_user_async(
    request: DeactivateUserRequest,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """
    Deactivate user asynchronously using Celery task.
    Requires system admin privileges.
    """
    # Check if target user exists
    target_user = session.get(AppUser, request.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deactivation
    if target_user.app_user_id == current_user.app_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Trigger Celery task for deactivation
    task = deactivate_user_with_resources.delay(
        str(request.user_id),
        str(current_user.app_user_id),
        request.reason
    )
    
    return {
        "success": True,
        "message": f"Deactivation task queued for user {target_user.user_email}",
        "task_id": task.id,
        "user_id": str(request.user_id)
    }


@router.post("/reactivate-async", response_model=dict)
async def reactivate_user_async(
    request: ReactivateUserRequest,
    current_user: AppUser = Depends(require_system_admin),
    session: Session = Depends(get_session)
):
    """
    Reactivate user asynchronously using Celery task.
    Requires system admin privileges.
    """
    # Check if target user exists
    target_user = session.get(AppUser, request.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Trigger Celery task for reactivation
    task = reactivate_user_with_resources.delay(
        str(request.user_id),
        str(current_user.app_user_id)
    )
    
    return {
        "success": True,
        "message": f"Reactivation task queued for user {target_user.user_email}",
        "task_id": task.id,
        "user_id": str(request.user_id)
    }