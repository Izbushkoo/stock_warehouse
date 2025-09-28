"""Middleware for warehouse service."""

from warehouse_service.middleware.auth import AuthMiddleware

__all__ = ["AuthMiddleware"]