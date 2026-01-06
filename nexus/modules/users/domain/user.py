"""
User Domain Model

Pure data model representing a user entity.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User domain model."""
    id: int
    auth_id: str
    email: str
    name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary (e.g., from database row)."""
        return cls(
            id=data["id"],
            auth_id=data["auth_id"],
            email=data["email"],
            name=data.get("name"),
            role=data.get("role", "user"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at") or datetime.utcnow(),
            updated_at=data.get("updated_at") or datetime.utcnow(),
        )
    
    def to_dict(self) -> dict:
        """Convert User to dictionary."""
        return {
            "id": self.id,
            "auth_id": self.auth_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

