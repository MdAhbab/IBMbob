"""
WebSocket package for real-time communication.
"""

from .manager import ConnectionManager, connection_manager
from .terminals import router as terminals_router

__all__ = ["ConnectionManager", "connection_manager", "terminals_router"]
