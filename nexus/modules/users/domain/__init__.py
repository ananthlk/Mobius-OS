"""
Domain Models

Pure data models representing user and profile entities.
"""

from .user import User
from .profile import (
    BasicProfile,
    ProfessionalProfile,
    CommunicationProfile,
    UseCaseProfile,
    AIPreferenceProfile,
    QueryHistoryProfile,
)
from .events import ProfileEvent

__all__ = [
    "User",
    "BasicProfile",
    "ProfessionalProfile",
    "CommunicationProfile",
    "UseCaseProfile",
    "AIPreferenceProfile",
    "QueryHistoryProfile",
    "ProfileEvent",
]



