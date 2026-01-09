"""
Migration Models

Data models for migration metadata.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class MigrationStatus(Enum):
    """Migration execution status."""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"


@dataclass
class Migration:
    """
    Represents a database migration.
    """
    number: int
    filename: str
    filepath: str
    status: MigrationStatus = MigrationStatus.PENDING
    applied_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        return f"Migration({self.number:03d}_{self.filename})"
    
    def __repr__(self) -> str:
        return self.__str__()




