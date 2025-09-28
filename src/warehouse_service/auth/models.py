"""Authentication models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID


class UserResponse(BaseModel):
    """User response model."""
    user_id: UUID
    email: str
    display_name: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    """Create user request."""
    email: EmailStr
    display_name: str
    password: str
    is_active: bool = True