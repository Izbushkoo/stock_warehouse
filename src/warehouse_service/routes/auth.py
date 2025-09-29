"""Authentication routes."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session

from warehouse_service.auth import (
    AuthService, LoginRequest, TokenResponse, UserResponse, 
    CreateUserRequest, PasswordChangeRequest, get_current_user
)
from warehouse_service.auth.dependencies import get_session, get_auth_service
from warehouse_service.models.unified import AppUser
from warehouse_service.auth.permissions_v2 import PermissionManager

auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login user and return access token."""
    token_response = auth_service.login(request)
    
    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    return token_response


@auth_router.post("/register", response_model=UserResponse)
async def register(
    request: CreateUserRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register new user."""
    try:
        user = auth_service.create_user(request)
        return auth_service.get_user_response(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: AppUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current user information."""
    return auth_service.get_user_response(current_user)


@auth_router.get("/me/permissions")
async def get_current_user_with_permissions(
    request: Request,
    current_user: AppUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current user information with permissions."""
    user_data = auth_service.get_user_response(current_user)
    user_permissions = getattr(request.state, "user_permissions", {})
    
    return {
        **user_data.model_dump(),
        "permissions": user_permissions
    }


@auth_router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: AppUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change user password."""
    success = auth_service.change_password(
        current_user.app_user_id,
        request.current_password,
        request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    return {"message": "Password changed successfully"}


@auth_router.get("/permissions")
async def get_user_permissions(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get current user's permissions."""
    pm = PermissionManager(session)
    permissions = pm.get_user_warehouse_permissions(current_user.app_user_id)
    
    return {
        "user_id": str(current_user.app_user_id),
        "email": current_user.user_email,
        "permissions": permissions
    }


@auth_router.get("/users-test")
async def test_users_endpoint():
    """Test endpoint to verify routing works."""
    return {"message": "Users endpoint is working", "count": 0}


@auth_router.get("/users", response_model=List[UserResponse])
async def list_users(
    request: Request,
    current_user: AppUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get list of all users (admin only)."""
    # Проверяем права доступа через middleware
    user_permissions = getattr(request.state, "user_permissions", {})
    
    if not (user_permissions.get("is_admin") or user_permissions.get("can_manage_users")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list users"
        )
    
    users = auth_service.list_users()
    return [auth_service.get_user_response(user) for user in users]





@auth_router.post("/logout")
async def logout():
    """Logout user (client should discard token)."""
    return {"message": "Logged out successfully"}


__all__ = ["auth_router"]