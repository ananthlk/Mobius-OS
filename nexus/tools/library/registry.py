"""
Tool Library Registry - Manages tools stored in database
"""
import json
import logging
from typing import Dict, List, Optional, Any
from nexus.modules.database import database

logger = logging.getLogger("nexus.tool_library")

class ToolLibraryRegistry:
    """Manages the tool library - CRUD operations for tools."""
    
    async def get_all_active_tools(self) -> List[Dict[str, Any]]:
        """Get all active tools with their parameters and execution conditions."""
        query = """
            SELECT 
                t.*,
                COALESCE(
                    (
                        SELECT json_agg(
                            jsonb_build_object(
                                'parameter_name', tp.parameter_name,
                                'parameter_type', tp.parameter_type,
                                'description', tp.description,
                                'is_required', tp.is_required,
                                'default_value', tp.default_value,
                                'validation_rules', tp.validation_rules,
                                'order_index', tp.order_index
                            ) ORDER BY tp.order_index
                        )
                        FROM tool_parameters tp
                        WHERE tp.tool_id = t.id
                    ),
                    '[]'::json
                ) as parameters,
                COALESCE(
                    (
                        SELECT json_agg(
                            jsonb_build_object(
                                'id', tec.id,
                                'condition_type', tec.condition_type,
                                'condition_expression', tec.condition_expression,
                                'action_type', tec.action_type,
                                'action_target_tool_id', tec.action_target_tool_id,
                                'action_target_tool_name', tec.action_target_tool_name,
                                'condition_description', tec.condition_description,
                                'icon_name', tec.icon_name,
                                'icon_color', tec.icon_color,
                                'execution_order', tec.execution_order
                            ) ORDER BY tec.execution_order
                        )
                        FROM tool_execution_conditions tec
                        WHERE tec.tool_id = t.id AND tec.is_active = true
                    ),
                    '[]'::json
                ) as execution_conditions
            FROM tools t
            WHERE t.status = 'active' AND t.is_public = true
            ORDER BY t.category, t.display_name
        """
        
        results = await database.fetch_all(query=query)
        
        tools = []
        for row in results:
            tool_dict = dict(row)
            # Parse JSONB fields
            if isinstance(tool_dict.get('schema_definition'), str):
                tool_dict['schema_definition'] = json.loads(tool_dict['schema_definition'])
            if isinstance(tool_dict.get('implementation_config'), str):
                tool_dict['implementation_config'] = json.loads(tool_dict['implementation_config'])
            if isinstance(tool_dict.get('parameters'), str):
                tool_dict['parameters'] = json.loads(tool_dict['parameters'])
            if isinstance(tool_dict.get('execution_conditions'), str):
                tool_dict['execution_conditions'] = json.loads(tool_dict['execution_conditions'])
            if isinstance(tool_dict.get('conditional_execution_examples'), str):
                tool_dict['conditional_execution_examples'] = json.loads(tool_dict['conditional_execution_examples'])
            tools.append(tool_dict)
        
        return tools
    
    async def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by name."""
        query = """
            SELECT 
                t.*,
                COALESCE(
                    (
                        SELECT json_agg(
                            jsonb_build_object(
                                'parameter_name', tp.parameter_name,
                                'parameter_type', tp.parameter_type,
                                'description', tp.description,
                                'is_required', tp.is_required,
                                'default_value', tp.default_value,
                                'validation_rules', tp.validation_rules,
                                'order_index', tp.order_index
                            ) ORDER BY tp.order_index
                        )
                        FROM tool_parameters tp
                        WHERE tp.tool_id = t.id
                    ),
                    '[]'::json
                ) as parameters,
                COALESCE(
                    (
                        SELECT json_agg(
                            jsonb_build_object(
                                'id', tec.id,
                                'condition_type', tec.condition_type,
                                'condition_expression', tec.condition_expression,
                                'action_type', tec.action_type,
                                'action_target_tool_id', tec.action_target_tool_id,
                                'action_target_tool_name', tec.action_target_tool_name,
                                'condition_description', tec.condition_description,
                                'icon_name', tec.icon_name,
                                'icon_color', tec.icon_color,
                                'execution_order', tec.execution_order
                            ) ORDER BY tec.execution_order
                        )
                        FROM tool_execution_conditions tec
                        WHERE tec.tool_id = t.id AND tec.is_active = true
                    ),
                    '[]'::json
                ) as execution_conditions
            FROM tools t
            WHERE t.name = :name AND t.status = 'active'
        """
        
        result = await database.fetch_one(query=query, values={"name": tool_name})
        
        if not result:
            return None
        
        tool_dict = dict(result)
        # Parse JSONB fields
        if isinstance(tool_dict.get('schema_definition'), str):
            tool_dict['schema_definition'] = json.loads(tool_dict['schema_definition'])
        if isinstance(tool_dict.get('implementation_config'), str):
            tool_dict['implementation_config'] = json.loads(tool_dict['implementation_config'])
        if isinstance(tool_dict.get('parameters'), str):
            tool_dict['parameters'] = json.loads(tool_dict['parameters'])
        if isinstance(tool_dict.get('execution_conditions'), str):
            tool_dict['execution_conditions'] = json.loads(tool_dict['execution_conditions'])
        if isinstance(tool_dict.get('conditional_execution_examples'), str):
            tool_dict['conditional_execution_examples'] = json.loads(tool_dict['conditional_execution_examples'])
        
        return tool_dict
    
    async def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools filtered by category."""
        query = """
            SELECT 
                t.*,
                COALESCE(
                    (
                        SELECT json_agg(
                            jsonb_build_object(
                                'parameter_name', tp.parameter_name,
                                'parameter_type', tp.parameter_type,
                                'description', tp.description,
                                'is_required', tp.is_required,
                                'default_value', tp.default_value,
                                'validation_rules', tp.validation_rules,
                                'order_index', tp.order_index
                            ) ORDER BY tp.order_index
                        )
                        FROM tool_parameters tp
                        WHERE tp.tool_id = t.id
                    ),
                    '[]'::json
                ) as parameters,
                COALESCE(
                    (
                        SELECT json_agg(
                            jsonb_build_object(
                                'id', tec.id,
                                'condition_type', tec.condition_type,
                                'condition_expression', tec.condition_expression,
                                'action_type', tec.action_type,
                                'action_target_tool_id', tec.action_target_tool_id,
                                'action_target_tool_name', tec.action_target_tool_name,
                                'condition_description', tec.condition_description,
                                'icon_name', tec.icon_name,
                                'icon_color', tec.icon_color,
                                'execution_order', tec.execution_order
                            ) ORDER BY tec.execution_order
                        )
                        FROM tool_execution_conditions tec
                        WHERE tec.tool_id = t.id AND tec.is_active = true
                    ),
                    '[]'::json
                ) as execution_conditions
            FROM tools t
            WHERE t.category = :category AND t.status = 'active' AND t.is_public = true
            ORDER BY t.display_name
        """
        
        results = await database.fetch_all(query=query, values={"category": category})
        
        tools = []
        for row in results:
            tool_dict = dict(row)
            if isinstance(tool_dict.get('schema_definition'), str):
                tool_dict['schema_definition'] = json.loads(tool_dict['schema_definition'])
            if isinstance(tool_dict.get('implementation_config'), str):
                tool_dict['implementation_config'] = json.loads(tool_dict['implementation_config'])
            if isinstance(tool_dict.get('parameters'), str):
                tool_dict['parameters'] = json.loads(tool_dict['parameters'])
            if isinstance(tool_dict.get('execution_conditions'), str):
                tool_dict['execution_conditions'] = json.loads(tool_dict['execution_conditions'])
            if isinstance(tool_dict.get('conditional_execution_examples'), str):
                tool_dict['conditional_execution_examples'] = json.loads(tool_dict['conditional_execution_examples'])
            tools.append(tool_dict)
        
        return tools
    
    async def register_tool(self, tool_data: Dict[str, Any], created_by: Optional[int] = None) -> Dict[str, Any]:
        """Register a new tool in the library."""
        # Insert tool
        tool_query = """
            INSERT INTO tools (
                name, display_name, description, category, version,
                schema_definition, requires_human_review, is_batch_processable,
                estimated_execution_time_ms, timeout_ms, is_deterministic,
                is_stateless, supports_async, implementation_type,
                implementation_path, implementation_config, author, tags,
                documentation_url, example_usage, status, is_public, created_by
            ) VALUES (
                :name, :display_name, :description, :category, :version,
                :schema_definition, :requires_human_review, :is_batch_processable,
                :estimated_execution_time_ms, :timeout_ms, :is_deterministic,
                :is_stateless, :supports_async, :implementation_type,
                :implementation_path, :implementation_config, :author, :tags,
                :documentation_url, :example_usage, :status, :is_public, :created_by
            ) RETURNING id
        """
        
        tool_result = await database.fetch_one(
            query=tool_query,
            values={
                "name": tool_data["name"],
                "display_name": tool_data["display_name"],
                "description": tool_data["description"],
                "category": tool_data["category"],
                "version": tool_data.get("version", "1.0.0"),
                "schema_definition": json.dumps(tool_data["schema_definition"]),
                "requires_human_review": tool_data.get("requires_human_review", False),
                "is_batch_processable": tool_data.get("is_batch_processable", False),
                "estimated_execution_time_ms": tool_data.get("estimated_execution_time_ms"),
                "timeout_ms": tool_data.get("timeout_ms", 30000),
                "is_deterministic": tool_data.get("is_deterministic", True),
                "is_stateless": tool_data.get("is_stateless", True),
                "supports_async": tool_data.get("supports_async", False),
                "implementation_type": tool_data.get("implementation_type", "python_class"),
                "implementation_path": tool_data.get("implementation_path"),
                "implementation_config": json.dumps(tool_data.get("implementation_config")) if tool_data.get("implementation_config") else None,
                "author": tool_data.get("author"),
                "tags": tool_data.get("tags", []),
                "documentation_url": tool_data.get("documentation_url"),
                "example_usage": tool_data.get("example_usage"),
                "status": tool_data.get("status", "active"),
                "is_public": tool_data.get("is_public", True),
                "created_by": created_by
            }
        )
        
        tool_id = tool_result["id"]
        
        # Insert parameters
        if tool_data.get("parameters"):
            param_query = """
                INSERT INTO tool_parameters (
                    tool_id, parameter_name, parameter_type, description,
                    is_required, default_value, validation_rules, order_index
                ) VALUES (
                    :tool_id, :parameter_name, :parameter_type, :description,
                    :is_required, :default_value, :validation_rules, :order_index
                )
            """
            for idx, param in enumerate(tool_data["parameters"]):
                await database.execute(
                    query=param_query,
                    values={
                        "tool_id": tool_id,
                        "parameter_name": param["parameter_name"],
                        "parameter_type": param["parameter_type"],
                        "description": param.get("description"),
                        "is_required": param.get("is_required", False),
                        "default_value": param.get("default_value"),
                        "validation_rules": json.dumps(param.get("validation_rules")) if param.get("validation_rules") else None,
                        "order_index": param.get("order_index", idx)
                    }
                )
        
        # Insert execution conditions
        if tool_data.get("execution_conditions"):
            condition_query = """
                INSERT INTO tool_execution_conditions (
                    tool_id, condition_type, condition_expression, action_type,
                    action_target_tool_id, action_target_tool_name, condition_description,
                    icon_name, icon_color, execution_order
                ) VALUES (
                    :tool_id, :condition_type, :condition_expression, :action_type,
                    :action_target_tool_id, :action_target_tool_name, :condition_description,
                    :icon_name, :icon_color, :execution_order
                )
            """
            for idx, condition in enumerate(tool_data["execution_conditions"]):
                # Look up target tool ID if target_tool_name is provided
                target_tool_id = condition.get("action_target_tool_id")
                if not target_tool_id and condition.get("action_target_tool_name"):
                    target_tool = await self.get_tool_by_name(condition["action_target_tool_name"])
                    if target_tool:
                        target_tool_id = target_tool["id"]
                
                await database.execute(
                    query=condition_query,
                    values={
                        "tool_id": tool_id,
                        "condition_type": condition["condition_type"],
                        "condition_expression": json.dumps(condition["condition_expression"]),
                        "action_type": condition["action_type"],
                        "action_target_tool_id": target_tool_id,
                        "action_target_tool_name": condition.get("action_target_tool_name"),
                        "condition_description": condition.get("condition_description"),
                        "icon_name": condition.get("icon_name"),
                        "icon_color": condition.get("icon_color"),
                        "execution_order": condition.get("execution_order", idx)
                    }
                )
        
        return await self.get_tool_by_name(tool_data["name"])

# Global registry instance
tool_registry = ToolLibraryRegistry()

