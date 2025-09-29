"""Authentication and authorization middleware."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from warehouse_service.auth.auth_service import AuthService
from warehouse_service.db import session_scope
from warehouse_service.models.unified import AppUser
from warehouse_service.rbac.unified import RBACService, WarehouseOperation, AccessContext

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and authorization."""
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/health",
        "/api/status",
        "/api/auth/login",
        "/api/auth/register",
        "/auth/login",
        "/auth/register",
        "/register",
        "/static",
        "/favicon.ico"
    }
    
    # Paths that require authentication but no specific permissions
    AUTH_ONLY_PATHS = {
        "/api/auth/me",
        "/api/auth/permissions", 
        "/api/auth/change-password",
        "/api/auth/logout"
    }
    
    # Permission mapping for API endpoints
    PERMISSION_RULES = [
        # Warehouse endpoints
        {
            "pattern": r"^/api/v1/warehouses$",
            "methods": ["GET"],
            "operation": None,  # Special case - handled in middleware
        },
        {
            "pattern": r"^/api/v1/warehouses/([^/]+)/stock-balance$",
            "methods": ["GET"],
            "operation": WarehouseOperation.VIEW_INVENTORY,
            "warehouse_param": 1,
        },
        {
            "pattern": r"^/api/v1/warehouses/([^/]+)/movements$",
            "methods": ["GET"],
            "operation": WarehouseOperation.VIEW_INVENTORY,
            "warehouse_param": 1,
        },
        {
            "pattern": r"^/api/v1/stock-movements$",
            "methods": ["POST"],
            "operation": WarehouseOperation.CREATE_MOVEMENT,
            "warehouse_from_body": "warehouse_id",
        },
        # Sales order endpoints
        {
            "pattern": r"^/api/v1/sales-orders$",
            "methods": ["POST"],
            "operation": WarehouseOperation.CREATE_SALES_ORDER,
            "warehouse_from_body": "warehouse_id",
        },
        {
            "pattern": r"^/api/v1/sales-orders/([^/]+)/allocate$",
            "methods": ["POST"],
            "operation": WarehouseOperation.CREATE_SALES_ORDER,
            "warehouse_from_order": True,
        },
        {
            "pattern": r"^/api/v1/sales-orders/([^/]+)/ship$",
            "methods": ["POST"],
            "operation": WarehouseOperation.SHIP_SALES_ORDER,
            "warehouse_from_order": True,
        },
        # Analytics endpoints
        {
            "pattern": r"^/api/v1/warehouses/([^/]+)/analytics/",
            "methods": ["GET"],
            "operation": WarehouseOperation.VIEW_ANALYTICS,
            "warehouse_param": 1,
        },
        {
            "pattern": r"^/api/v1/warehouses/([^/]+)/purchase-recommendations$",
            "methods": ["POST"],
            "operation": WarehouseOperation.VIEW_ANALYTICS,
            "warehouse_param": 1,
        },
    ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication and authorization middleware."""
        
        # Skip auth for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Get user from token
        user = await self._get_user_from_request(request)
        
        # Add user to request state
        request.state.user = user
        
        # Add user permissions to request state for API usage
        if user:
            with session_scope() as session:
                from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType
                pm = PermissionManager(session)
                is_system_admin = pm.is_system_admin(user.app_user_id)
                user_permissions = pm.get_user_permissions(user.app_user_id)
                
                # Check if user has access to any warehouses
                has_warehouse_access = any(
                    perm["resource_type"] == ResourceType.WAREHOUSE.value 
                    for perm in user_permissions
                ) or is_system_admin
                
                request.state.user_permissions = {
                    "is_admin": is_system_admin,
                    "can_manage_users": is_system_admin,
                    "has_warehouse_access": has_warehouse_access,
                    "warehouses": {},  # TODO: implement warehouse-specific permissions
                    "total_grants": len(user_permissions),
                    "permissions": user_permissions
                }
        else:
            request.state.user_permissions = {
                "is_admin": False,
                "can_manage_users": False,
                "has_warehouse_access": False,
                "warehouses": {},
                "total_grants": 0,
                "permissions": []
            }
        
        # Check if path requires authentication
        if self._requires_auth(request.url.path):
            if not user:
                return await self._handle_unauthenticated(request)
            
            if not user.is_active:
                return await self._handle_inactive_user(request)
        
        # Check permissions for API endpoints
        if request.url.path.startswith("/api/v1/"):
            permission_check = await self._check_api_permissions(request, user)
            if permission_check is not None:
                return permission_check
        
        response = await call_next(request)
        return response
    
    async def _check_api_permissions(self, request: Request, user: AppUser) -> Optional[Response]:
        """Check API endpoint permissions."""
        if not user:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )
        
        path = request.url.path
        method = request.method
        
        # Find matching permission rule
        for rule in self.PERMISSION_RULES:
            pattern_match = re.match(rule["pattern"], path)
            if pattern_match and method in rule["methods"]:
                operation = rule.get("operation")
                
                if operation is None:
                    # Special case handling (like listing warehouses)
                    continue
                
                # Extract warehouse_id from various sources
                warehouse_id = await self._extract_warehouse_id(request, rule, pattern_match)
                
                if not warehouse_id:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Could not determine warehouse context"}
                    )
                
                # Check permission
                with session_scope() as session:
                    rbac = RBACService(session)
                    context = AccessContext(warehouse_id=warehouse_id)
                    
                    if not rbac.check_permission(user.app_user_id, operation, context):
                        return JSONResponse(
                            status_code=403,
                            content={"detail": f"Insufficient permissions for {operation.value}"}
                        )
                
                # Permission granted, continue
                break
        
        return None
    
    async def _extract_warehouse_id(self, request: Request, rule: Dict[str, Any], pattern_match) -> Optional[UUID]:
        """Extract warehouse_id from request based on rule configuration."""
        
        # From URL parameter
        if "warehouse_param" in rule:
            param_index = rule["warehouse_param"]
            try:
                return UUID(pattern_match.group(param_index))
            except (ValueError, IndexError):
                return None
        
        # From request body
        if "warehouse_from_body" in rule:
            try:
                # Cache body for later use by the endpoint
                if not hasattr(request.state, 'body'):
                    body = await request.body()
                    request.state.body = body
                else:
                    body = request.state.body
                
                if body:
                    data = json.loads(body)
                    warehouse_id_str = data.get(rule["warehouse_from_body"])
                    if warehouse_id_str:
                        return UUID(warehouse_id_str)
            except (json.JSONDecodeError, ValueError):
                pass
            return None
        
        # From sales order lookup
        if rule.get("warehouse_from_order"):
            try:
                sales_order_id = UUID(pattern_match.group(1))
                with session_scope() as session:
                    from warehouse_service.models.unified import SalesOrder
                    order = session.get(SalesOrder, sales_order_id)
                    if order:
                        return order.warehouse_id
            except (ValueError, IndexError):
                pass
            return None
        
        return None
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)."""
        # Exact matches
        if path in self.PUBLIC_PATHS:
            return True
        
        # Prefix matches for static files, etc.
        public_prefixes = ["/static/", "/favicon"]
        return any(path.startswith(prefix) for prefix in public_prefixes)
    
    def _requires_auth(self, path: str) -> bool:
        """Check if path requires authentication."""
        # API paths require auth (except public ones already filtered)
        if path.startswith("/api/"):
            return True
        
        
        # Auth-only paths
        if path in self.AUTH_ONLY_PATHS:
            return True
        
        return False
    
    async def _get_user_from_request(self, request: Request) -> Optional[AppUser]:
        """Extract and validate user from request."""
        try:
            # Try to get token from Authorization header
            auth_header = request.headers.get("Authorization")
            token = None
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
            
            # Try to get token from cookie (for web interface)
            if not token:
                token = request.cookies.get("access_token")
            
            if not token:
                return None
            
            # Validate token and get user
            with session_scope() as session:
                auth_service = AuthService(session)
                user = auth_service.get_user_by_token(token)
                if user:
                    # Create a detached copy of the user to avoid session issues
                    detached_user = AppUser(
                        app_user_id=user.app_user_id,
                        user_email=user.user_email,
                        user_display_name=user.user_display_name,
                        password_hash=user.password_hash,
                        is_active=user.is_active,
                        last_login_at=user.last_login_at,
                        created_at=user.created_at
                    )
                    return detached_user
                return None
                
        except Exception as e:
            logger.warning(f"Error getting user from request: {e}")
            return None
    
    async def _handle_unauthenticated(self, request: Request) -> Response:
        """Handle unauthenticated requests."""
        # For API requests, return JSON error
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )
        
        # For web requests, redirect to login
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"}
        )
    
    async def _handle_inactive_user(self, request: Request) -> Response:
        """Handle requests from inactive users."""
        # For API requests, return JSON error
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "User account is disabled"}
            )
        
        # For web requests, redirect to login with message
        return JSONResponse(
            status_code=403,
            content={"detail": "Account is disabled"}
        )