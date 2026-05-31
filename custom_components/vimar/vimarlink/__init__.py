"""Vimar Link package - Modular version."""

from .connection import VimarConnection
from .device_queries import VimarDevice
from .exceptions import VimarApiError, VimarConfigError, VimarConnectionError
from .vimarlink import VimarLink, VimarProject

__all__ = [
    "VimarConnection",
    "VimarDevice",
    "VimarApiError",
    "VimarConfigError",
    "VimarConnectionError",
    "VimarLink",
    "VimarProject",
]
