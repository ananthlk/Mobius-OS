"""
Data Access Layer (Repositories)

Repositories handle all database interactions.
"""

from .user_repository import UserRepository
from .profile_repository import ProfileRepository

__all__ = [
    "UserRepository",
    "ProfileRepository",
]

