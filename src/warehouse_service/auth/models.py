"""Authentication models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator
import re


class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format allowing .local domains."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()


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
    email: str
    display_name: str
    password: str
    is_active: bool = True
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format allowing .local domains."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()
