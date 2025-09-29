"""Authentication service."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

import bcrypt
import jwt
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from warehouse_service.auth.password import hash_password, verify_password
from warehouse_service.auth.user_lifecycle import UserLifecycleService

from warehouse_service.auth.models import (
    CreateUserRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from warehouse_service.config import get_settings
from warehouse_service.models.unified import AppUser, Permission


class AuthService:
    """Service for authentication and user management."""
    
    def __init__(
        self,
        session: Session,
        secret_key: str | None = None,
        algorithm: str | None = None,
        token_expire_hours: int | None = None,
    ):
        self.session = session
        security_settings = get_settings().security
        self.secret_key = secret_key or security_settings.jwt_secret
        self.algorithm = algorithm or security_settings.jwt_algorithm
        self.token_expire_hours = token_expire_hours or security_settings.jwt_expire_hours
    
    def authenticate_user(self, email: str, password: str) -> Optional[AppUser]:
        """Authenticate user by email and password."""
        stmt = select(AppUser).where(
            AppUser.user_email == email,
            AppUser.is_active == True
        )
        user = self.session.exec(stmt).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
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
        password_hash = hash_password(request.password)
        
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

    def list_users(self) -> List[AppUser]:
        """Return all application users ordered by email."""
        stmt = select(AppUser).order_by(AppUser.user_email)
        return list(self.session.exec(stmt))

    def get_user(self, user_id: UUID) -> Optional[AppUser]:
        """Get user by identifier."""
        return self.session.get(AppUser, user_id)


    
    def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.session.get(AppUser, user_id)
        if not user:
            return False
        
        if not verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = hash_password(new_password)
        self.session.add(user)
        self.session.commit()
        
        return True
    
    def deactivate_user_cascade(self, user_id: UUID, deactivated_by: UUID, reason: Optional[str] = None) -> bool:
        """Deactivate user and soft delete all their created resources."""
        lifecycle_service = UserLifecycleService(self.session)
        return lifecycle_service.deactivate_user(user_id, deactivated_by, reason)
    
    def reactivate_user_cascade(self, user_id: UUID, reactivated_by: UUID) -> bool:
        """Reactivate user and restore all their soft deleted resources."""
        lifecycle_service = UserLifecycleService(self.session)
        return lifecycle_service.reactivate_user(user_id, reactivated_by)
    
    def get_users_for_permanent_deletion(self, days_threshold: int = 30) -> List[AppUser]:
        """Get users eligible for permanent deletion after being deactivated for specified days."""
        lifecycle_service = UserLifecycleService(self.session)
        return lifecycle_service.get_users_for_permanent_deletion(days_threshold)
    
    def permanently_delete_user(self, user_id: UUID) -> bool:
        """Permanently delete user and all their soft deleted resources."""
        lifecycle_service = UserLifecycleService(self.session)
        return lifecycle_service.permanently_delete_user(user_id)
    
    def update_user_status(self, user_id: str, is_active: bool) -> AppUser:
        """Update user active status."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("Invalid user ID format")
        
        user = self.session.get(AppUser, user_uuid)
        if not user:
            raise ValueError("User not found")
        
        user.is_active = is_active
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        return user
    
    def update_user_permissions(self, user_id: str, permissions_data: dict) -> AppUser:
        """Update user permissions using the Permission system."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("Invalid user ID format")
        
        user = self.session.get(AppUser, user_uuid)
        if not user:
            raise ValueError("User not found")
        
        from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType, PermissionLevel
        
        pm = PermissionManager(self.session)
        
        # Системный ресурс ID
        system_resource_id = UUID("00000000-0000-0000-0000-000000000001")
        
        # Удаляем существующие системные разрешения
        existing_system_perms = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_uuid,
                Permission.resource_type == ResourceType.SYSTEM.value
            )
        ).all()
        
        for perm in existing_system_perms:
            self.session.delete(perm)
        
        # Добавляем новые системные разрешения
        if permissions_data.get("is_admin", False):
            permission = Permission(
                app_user_id=user_uuid,
                resource_type=ResourceType.SYSTEM.value,
                resource_id=system_resource_id,
                permission_level=PermissionLevel.ADMIN.value,
                granted_by=user_uuid,  # TODO: передавать ID того, кто выдает разрешения
                is_active=True
            )
            self.session.add(permission)
        
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def update_user_permissions_with_granter(self, user_id: str, permissions_data: dict, granted_by: UUID) -> AppUser:
        """Update user permissions with proper granter tracking."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("Invalid user ID format")
        
        user = self.session.get(AppUser, user_uuid)
        if not user:
            raise ValueError("User not found")
        
        from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType, PermissionLevel
        
        pm = PermissionManager(self.session)
        
        # Системный ресурс ID
        system_resource_id = UUID("00000000-0000-0000-0000-000000000001")
        
        # Удаляем существующие системные разрешения
        existing_system_perms = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_uuid,
                Permission.resource_type == ResourceType.SYSTEM.value
            )
        ).all()
        
        for perm in existing_system_perms:
            self.session.delete(perm)
        
        # Добавляем новые системные разрешения
        if permissions_data.get("is_admin", False):
            permission = Permission(
                app_user_id=user_uuid,
                resource_type=ResourceType.SYSTEM.value,
                resource_id=system_resource_id,
                permission_level=PermissionLevel.ADMIN.value,
                granted_by=granted_by,
                is_active=True
            )
            self.session.add(permission)
        
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def update_user(self, user_id: str, user_data: dict) -> AppUser:
        """Update user information with dict data."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("Invalid user ID format")
        
        user = self.session.get(AppUser, user_uuid)
        if not user:
            raise ValueError("User not found")
        
        # Update allowed fields
        if 'display_name' in user_data:
            user.user_display_name = user_data['display_name']
        
        if 'email' in user_data:
            # Check if email is already taken
            existing = self.session.exec(
                select(AppUser).where(
                    AppUser.user_email == user_data['email'],
                    AppUser.app_user_id != user_uuid
                )
            ).first()
            if existing:
                raise ValueError(f"User with email {user_data['email']} already exists")
            user.user_email = user_data['email']
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        return user
    
    def delete_user(self, user_id: str) -> None:
        """Delete user by string ID."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("Invalid user ID format")
        
        user = self.session.get(AppUser, user_uuid)
        if not user:
            raise ValueError("User not found")

        # Удаляем все разрешения пользователя
        permissions = self.session.exec(
            select(Permission).where(
                Permission.app_user_id == user_uuid
            )
        ).all()

        try:
            for permission in permissions:
                self.session.delete(permission)

            self.session.delete(user)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError("Cannot delete user due to related records") from exc
    
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
    
