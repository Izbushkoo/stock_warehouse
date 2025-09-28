"""Unified warehouse service package."""

from importlib import metadata as _metadata

__all__ = ["__version__"]

try:
    __version__ = _metadata.version("warehouse-service")
except _metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
