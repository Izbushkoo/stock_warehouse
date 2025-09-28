"""System health checks executed on startup and scheduled intervals."""

from __future__ import annotations

from warehouse_service.system_checks.runner import run_checks

__all__ = ["run_checks"]
