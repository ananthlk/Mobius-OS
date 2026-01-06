"""
Authentication and Authorization Module

Provides:
- Authentication middleware
- Session management
- Role-based access control (RBAC)
"""

from .middleware import get_current_user, get_optional_user, require_admin, get_or_create_user
from .permissions import check_permission, require_permission

__all__ = [
    "get_current_user",
    "get_optional_user",
    "require_admin",
    "get_or_create_user",
    "check_permission",
    "require_permission",
]
