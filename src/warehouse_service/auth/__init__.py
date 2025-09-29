"""Authentication and authorization system."""

from warehouse_service.auth.auth_service import AuthService
from warehouse_service.auth.dependencies import get_current_user, require_auth
from warehouse_service.auth.models import LoginRequest, TokenResponse, UserResponse, CreateUserRequest, PasswordChangeRequest
from warehouse_service.auth.permissions import is_admin, can_manage_users, require_admin, require_warehouse_access

__all__ = [
    "AuthService",
    "get_current_user", 
    "require_auth",
    "LoginRequest",
    "TokenResponse", 
    "UserResponse",
    "CreateUserRequest",
    "PasswordChangeRequest",
    "is_admin",
    "can_manage_users", 
    "require_admin",
    "require_warehouse_access"
]