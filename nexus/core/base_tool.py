from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class NexusTool(ABC):
    """
    Base class for all Deterministic Tools.
    'The Workhorse'.
    """
    def __init__(self):
        self.schema = self.define_schema()

    @abstractmethod
    def define_schema(self) -> ToolSchema:
        """
        Returns the JSON schema definition for this tool.
        Used by the Brain/Agent to understand inputs.
        """
        pass

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """
        Executes the tool logic.
        Must be stateless and deterministic given inputs.
        """
        pass
