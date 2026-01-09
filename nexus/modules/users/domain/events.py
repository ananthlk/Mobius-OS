"""
Profile Event Domain Model

Represents an event that might contain profile-relevant information.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ProfileEvent:
    """Represents an event that might contain profile-relevant information."""
    user_id: int
    event_type: str
    user_message: str
    assistant_response: str
    session_id: Optional[int] = None
    interaction_id: Optional[str] = None
    workflow_name: Optional[str] = None
    strategy: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.extracted_data is None:
            self.extracted_data = {}




