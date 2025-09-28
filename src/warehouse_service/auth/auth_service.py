"""Authentication service."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import bcrypt
import jwt
from sqlmodel import Session, select

from warehouse_service.models.unified import AppUser
from warehouse_service.auth.models import LoginRequest, TokenResponse, UserResponse, CreateUserRequest


class AuthService:
    """Service for authentication and user management."""
    
    def __init__(self, session: Session, secret_key: str = None):
        self.session = session
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.token_expire_hours = 24
    
    def authenticate_user(self, email: str, password: str) -> Optional[AppUser]:
        """Authenticate user by email and password."""
        stmt = select(AppUser).where(
            AppUser.user_email == email,
            AppUser.is_active == True
        )
        user = self.session.exec(stmt).first()
        
        if not user:
            return None
        
        if not self._verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        self.session.add(user)
        self.session.commit()
        
        return user
    
    def create_access_token(self, user: AppUser) -> TokenResponse:
        """Create JWT access token for user."""
        expire = datetime.utcnow() + timedelta(hours=self.token_expire_hours)
        
        payload = {
            "sub": str(user.app_user_id),
            "email": user.user_email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return TokenResponse(
            access_token=token,
            expires_in=self.token_expire_hours * 3600,
            user_id=user.app_user_id
        )
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_by_token(self, token: str) -> Optional[AppUser]:
        """Get user by JWT token."""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            return None
        
        return self.session.get(AppUser, user_uuid)
    
    def login(self, request: LoginRequest) -> Optional[TokenResponse]:
        """Login user and return token."""
        user = self.authenticate_user(request.email, request.password)
        if not user:
            return None
        
        return self.create_access_token(user)
    
    def create_user(self, request: CreateUserRequest) -> AppUser:
        """Create new user."""
        # Check if user already exists
        existing = self.session.exec(
            select(AppUser).where(AppUser.user_email == request.email)
        ).first()
        
        if existing:
            raise ValueError(f"User with email {request.email} already exists")
        
        # Hash password
        password_hash = self._hash_password(request.password)
        
        # Create user
        user = AppUser(
            user_email=request.email,
            user_display_name=request.display_name,
            password_hash=password_hash,
            is_active=request.is_active
        )
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        return user
    
    def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.session.get(AppUser, user_id)
        if not user:
            return False
        
        if not self._verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = self._hash_password(new_password)
        self.session.add(user)
        self.session.commit()
        
        return True
    
    def get_user_response(self, user: AppUser) -> UserResponse:
        """Convert user to response model."""
        return UserResponse(
            user_id=user.app_user_id,
            email=user.user_email,
            display_name=user.user_display_name,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
            created_at=user.created_at
        )
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))