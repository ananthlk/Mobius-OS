"""
Tool Loader - Dynamically loads tool instances from database definitions
"""
import importlib
import logging
from typing import Dict, Any, Optional
from nexus.core.base_tool import NexusTool

logger = logging.getLogger("nexus.tool_loader")

class ToolLoader:
    """Loads tool instances from database tool definitions."""
    
    def load_tool(self, tool_data: Dict[str, Any]) -> Optional[NexusTool]:
        """Load a tool instance from database definition."""
        implementation_type = tool_data.get("implementation_type", "python_class")
        implementation_path = tool_data.get("implementation_path")
        
        if not implementation_path:
            logger.warning(f"Tool {tool_data.get('name')} has no implementation_path")
            return None
        
        if implementation_type == "python_class":
            return self._load_python_class(implementation_path)
        elif implementation_type == "api_endpoint":
            # TODO: Implement API endpoint tool loading
            logger.warning(f"API endpoint tools not yet implemented for {tool_data.get('name')}")
            return None
        else:
            logger.warning(f"Unknown implementation type: {implementation_type} for {tool_data.get('name')}")
            return None
    
    def _load_python_class(self, class_path: str) -> Optional[NexusTool]:
        """Load a Python class from module path."""
        try:
            # Split module path: "nexus.tools.eligibility.gate1_data_retrieval.PatientDemographicsRetriever"
            parts = class_path.split(".")
            module_path = ".".join(parts[:-1])
            class_name = parts[-1]
            
            # Import module
            module = importlib.import_module(module_path)
            
            # Get class
            tool_class = getattr(module, class_name)
            
            # Instantiate
            tool_instance = tool_class()
            
            if not isinstance(tool_instance, NexusTool):
                logger.error(f"Loaded class {class_path} is not a NexusTool instance")
                return None
            
            return tool_instance
            
        except ImportError as e:
            logger.error(f"Failed to import module for {class_path}: {e}")
            return None
        except AttributeError as e:
            logger.error(f"Class {class_name} not found in module {module_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load tool {class_path}: {e}")
            return None

