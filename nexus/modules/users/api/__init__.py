"""
REST API Endpoints

Thin API layer that delegates to services.
"""

from .user_endpoints import router as user_router
from .profile_endpoints import router as profile_router

__all__ = [
    "user_router",
    "profile_router",
]

