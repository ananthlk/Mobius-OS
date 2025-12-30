from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from nexus.core.base_agent import AgentRecipe

class NexusBrain(ABC):
    """
    Base class for Strategy & Routing.
    'The Router'.
    """
    
    @abstractmethod
    async def route(self, intent: str, context: Dict[str, Any]) -> Optional[AgentRecipe]:
        """
        Analyzes the intent and returns the appropriate Recipe (Instructions)
        to be given to the Agent Factory.
        Returns None if no matching recipe found.
        """
        pass
