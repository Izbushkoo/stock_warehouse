"""Authentication dependencies for FastAPI."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from warehouse_service.db import session_scope
from warehouse_service.models.unified import AppUser
from warehouse_service.auth.auth_service import AuthService

security = HTTPBearer()


def get_session():
    """Get database session."""
    with session_scope() as session:
        yield session


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    """Get authentication service."""
    return AuthService(session)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> AppUser:
    """Get current authenticated user."""
    token = credentials.credentials
    user = auth_service.get_user_by_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[AppUser]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    token = credentials.credentials
    user = auth_service.get_user_by_token(token)
    
    if not user or not user.is_active:
        return None
    
    return user


def require_auth(user: AppUser = Depends(get_current_user)) -> AppUser:
    """Require authentication (alias for get_current_user)."""
    return user


def require_system_admin(
    user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> AppUser:
    """Require system admin privileges."""
    from warehouse_service.auth.permissions_v2 import require_system_admin as _require_system_admin
    
    _require_system_admin(user, session)
    return user