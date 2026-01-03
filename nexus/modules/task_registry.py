"""
Task Registry Module

Manages the task catalog - the master reference system for all tasks.
Tasks must exist in this catalog before being used in draft_plan.
"""
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
from datetime import datetime
from nexus.modules.database import database, parse_jsonb
from nexus.core.task_schema_validator import task_schema_validator

logger = logging.getLogger("nexus.task_registry")


class TaskRegistry:
    """Manages the task catalog - CRUD operations for tasks."""
    
    def __init__(self):
        self.validator = task_schema_validator
    
    async def create_task(self, task_data: Dict[str, Any], created_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Create new task in catalog.
        
        Args:
            task_data: Task data matching the schema
            created_by: User ID creating the task
        
        Returns:
            Created task data
        """
        # Validate schema
        is_valid, errors = self.validator.validate_task_schema(task_data)
        if not is_valid:
            raise ValueError(f"Task schema validation failed: {', '.join(errors)}")
        
        # Generate task_key if not provided
        if "task_key" not in task_data or not task_data["task_key"]:
            task_data["task_key"] = self._generate_task_key(task_data.get("name", "unnamed_task"))
        
        # Check if task_key already exists
        existing = await self.get_task_by_key(task_data["task_key"])
        if existing:
            raise ValueError(f"Task with key '{task_data['task_key']}' already exists")
        
        # Generate UUID if not provided
        if "task_id" not in task_data:
            task_data["task_id"] = str(uuid4())
        
        # Set defaults
        task_data.setdefault("status", "draft")
        task_data.setdefault("version", 1)
        task_data.setdefault("schema_version", "1.0")
        
        # Build JSONB fields with defaults
        classification = task_data.get("classification", {})
        contract = task_data.get("contract", {})
        automation = task_data.get("automation", {})
        tool_binding_defaults = task_data.get("tool_binding_defaults", {})
        information = task_data.get("information", {})
        policy = task_data.get("policy", {})
        temporal = task_data.get("temporal", {})
        escalation = task_data.get("escalation", {})
        dependencies = task_data.get("dependencies", {})
        failure = task_data.get("failure", {})
        ui = task_data.get("ui", {})
        governance = task_data.get("governance", {})
        
        query = """
            INSERT INTO task_catalog (
                task_id, task_key, name, description,
                classification, contract, automation, tool_binding_defaults,
                information, policy, temporal, escalation, dependencies,
                failure, ui, governance, status, version, schema_version,
                created_by, updated_by
            )
            VALUES (
                CAST(:task_id AS uuid), :task_key, :name, :description,
                CAST(:classification AS jsonb), CAST(:contract AS jsonb), CAST(:automation AS jsonb), CAST(:tool_binding_defaults AS jsonb),
                CAST(:information AS jsonb), CAST(:policy AS jsonb), CAST(:temporal AS jsonb), CAST(:escalation AS jsonb), CAST(:dependencies AS jsonb),
                CAST(:failure AS jsonb), CAST(:ui AS jsonb), CAST(:governance AS jsonb), :status, :version, :schema_version,
                :created_by, :updated_by
            )
            RETURNING *
        """
        
        values = {
            "task_id": task_data["task_id"],
            "task_key": task_data["task_key"],
            "name": task_data["name"],
            "description": task_data.get("description"),
            "classification": json.dumps(classification),
            "contract": json.dumps(contract),
            "automation": json.dumps(automation),
            "tool_binding_defaults": json.dumps(tool_binding_defaults),
            "information": json.dumps(information),
            "policy": json.dumps(policy),
            "temporal": json.dumps(temporal),
            "escalation": json.dumps(escalation),
            "dependencies": json.dumps(dependencies),
            "failure": json.dumps(failure),
            "ui": json.dumps(ui),
            "governance": json.dumps(governance),
            "status": task_data["status"],
            "version": task_data["version"],
            "schema_version": task_data["schema_version"],
            "created_by": created_by,
            "updated_by": created_by
        }
        
        result = await database.fetch_one(query=query, values=values)
        return self._task_row_to_dict(result)
    
    async def get_task_by_key(self, task_key: str) -> Optional[Dict[str, Any]]:
        """Get task by key."""
        query = "SELECT * FROM task_catalog WHERE task_key = :task_key"
        result = await database.fetch_one(query=query, values={"task_key": task_key})
        
        if not result:
            return None
        
        return self._task_row_to_dict(result)
    
    async def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by UUID."""
        query = "SELECT * FROM task_catalog WHERE task_id = CAST(:task_id AS uuid)"
        result = await database.fetch_one(query=query, values={"task_id": task_id})
        
        if not result:
            return None
        
        return self._task_row_to_dict(result)
    
    async def update_task(self, task_key: str, updates: Dict[str, Any], updated_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Update task (creates new version in history).
        
        Args:
            task_key: Task key to update
            updates: Dictionary of updates
            updated_by: User ID making the update
        
        Returns:
            Updated task data
        """
        # Get current task
        current_task = await self.get_task_by_key(task_key)
        if not current_task:
            raise ValueError(f"Task with key '{task_key}' not found")
        
        # Save current version to history
        await self._save_to_history(current_task, updated_by)
        
        # Merge updates with current task
        updated_task = {**current_task, **updates}
        updated_task["version"] = current_task["version"] + 1
        updated_task["updated_by"] = updated_by
        
        # Validate updated schema
        is_valid, errors = self.validator.validate_task_schema(updated_task)
        if not is_valid:
            raise ValueError(f"Updated task schema validation failed: {', '.join(errors)}")
        
        # Build update query (only update provided fields)
        set_clauses = ["updated_at_utc = CURRENT_TIMESTAMP", "version = :version", "updated_by = :updated_by"]
        values = {"task_key": task_key, "version": updated_task["version"], "updated_by": updated_by}
        
        # Update JSONB fields if provided
        jsonb_fields = [
            "classification", "contract", "automation", "tool_binding_defaults",
            "information", "policy", "temporal", "escalation", "dependencies",
            "failure", "ui", "governance"
        ]
        
        for field in jsonb_fields:
            if field in updates:
                set_clauses.append(f"{field} = CAST(:{field} AS jsonb)")
                values[field] = json.dumps(updated_task[field])
        
        # Update simple fields
        simple_fields = ["name", "description", "status", "schema_version"]
        for field in simple_fields:
            if field in updates:
                set_clauses.append(f"{field} = :{field}")
                values[field] = updated_task[field]
        
        if "deprecated_at_utc" in updates:
            if updates.get("status") == "deprecated":
                set_clauses.append("deprecated_at_utc = CURRENT_TIMESTAMP")
            else:
                set_clauses.append("deprecated_at_utc = NULL")
        
        query = f"UPDATE task_catalog SET {', '.join(set_clauses)} WHERE task_key = :task_key RETURNING *"
        
        result = await database.fetch_one(query=query, values=values)
        return self._task_row_to_dict(result)
    
    async def delete_task(self, task_key: str, soft_delete: bool = True) -> bool:
        """
        Delete/deprecate task.
        
        Args:
            task_key: Task key to delete
            soft_delete: If True, mark as deprecated; if False, hard delete
        
        Returns:
            True if successful
        """
        if soft_delete:
            await self.update_task(task_key, {"status": "deprecated"})
            return True
        else:
            query = "DELETE FROM task_catalog WHERE task_key = :task_key"
            await database.execute(query=query, values={"task_key": task_key})
            return True
    
    async def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List tasks with filters.
        
        Args:
            filters: Dictionary of filters (status, domain, category, etc.)
        
        Returns:
            List of tasks
        """
        filters = filters or {}
        where_clauses = []
        values = {}
        
        if "status" in filters:
            where_clauses.append("status = :status")
            values["status"] = filters["status"]
        else:
            # Default: exclude deprecated unless explicitly requested
            where_clauses.append("status != 'deprecated'")
        
        if "domain" in filters:
            where_clauses.append("classification->>'domain' = :domain")
            values["domain"] = filters["domain"]
        
        if "category" in filters:
            where_clauses.append("classification->>'category' = :category")
            values["category"] = filters["category"]
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT * FROM task_catalog WHERE {where_clause} ORDER BY name"
        
        results = await database.fetch_all(query=query, values=values)
        return [self._task_row_to_dict(row) for row in results]
    
    async def search_tasks(self, query_text: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search tasks by name, description, or classification.
        
        Args:
            query_text: Search text
            filters: Additional filters
        
        Returns:
            List of matching tasks
        """
        filters = filters or {}
        where_clauses = []
        values = {"search": f"%{query_text}%"}
        
        # Text search in name and description
        where_clauses.append("(name ILIKE :search OR description ILIKE :search)")
        
        # Apply additional filters
        if "status" in filters:
            where_clauses.append("status = :status")
            values["status"] = filters["status"]
        else:
            where_clauses.append("status != 'deprecated'")
        
        if "domain" in filters:
            where_clauses.append("classification->>'domain' = :domain")
            values["domain"] = filters["domain"]
        
        if "category" in filters:
            where_clauses.append("classification->>'category' = :category")
            values["category"] = filters["category"]
        
        where_clause = " AND ".join(where_clauses)
        query = f"SELECT * FROM task_catalog WHERE {where_clause} ORDER BY name"
        
        results = await database.fetch_all(query=query, values=values)
        return [self._task_row_to_dict(row) for row in results]
    
    async def validate_task_exists(self, task_key: str) -> bool:
        """Check if task exists in catalog."""
        task = await self.get_task_by_key(task_key)
        return task is not None
    
    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all active (non-deprecated) tasks."""
        return await self.list_tasks({"status": "active"})
    
    async def get_task_dependencies(self, task_key: str) -> List[str]:
        """Get task dependency keys."""
        task = await self.get_task_by_key(task_key)
        if not task:
            return []
        
        dependencies = task.get("dependencies", {})
        return dependencies.get("depends_on_task_keys", [])
    
    async def find_or_create_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find existing task by description or create a new one.
        This is the primary method for ensuring tasks exist in the catalog.
        
        Args:
            task_description: Description of the task
            context: Additional context (domain, etc.)
            created_by: User ID
        
        Returns:
            Full task dict with task_id, task_key, etc. (not just task_key)
        """
        context = context or {}
        
        # First, try to find existing task by searching for similar descriptions
        # Search for tasks with matching description (case-insensitive)
        existing_tasks = await self.search_tasks(
            query_text=task_description,
            filters={"status": "active"}  # Only search active tasks
        )
        
        # Look for exact or very similar match
        task_description_lower = task_description.lower().strip()
        for task in existing_tasks:
            # Check for exact match (case-insensitive)
            if task.get("description", "").lower().strip() == task_description_lower:
                return task  # Return full task dict
        
            # Check for close match (description contains our text or vice versa)
            existing_desc_lower = task.get("description", "").lower().strip()
            if (task_description_lower in existing_desc_lower or 
                existing_desc_lower in task_description_lower):
                # Very similar - reuse existing task
                return task  # Return full task dict
        
        # No existing task found - create a new one
        task = await self.register_task_from_conversation(
            task_description=task_description,
            context=context,
            created_by=created_by
        )
        return task  # Return full task dict (already includes task_id)
    
    async def register_task_from_conversation(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-register task from conversation text.
        Creates a minimal task entry that can be refined later.
        NOTE: This always creates a new task. Use find_or_create_task() for lookup/create logic.
        
        Args:
            task_description: Description of the task from conversation
            context: Additional context (domain, etc.)
            created_by: User ID
        
        Returns:
            Created task data
        """
        context = context or {}
        
        # Generate stable task_key from description (no timestamp)
        task_key = self._generate_task_key(task_description)
        
        # Check if task_key already exists - if so, return existing task
        existing = await self.get_task_by_key(task_key)
        if existing:
            return existing
        
        # Create minimal task data
        domain = context.get("domain", "general")
        category = self._infer_category_from_description(task_description)
        
        task_data = {
            "task_key": task_key,
            "name": task_description[:255],  # Truncate if needed
            "description": task_description,
            "classification": {
                "domain": domain,
                "category": category,
                "tags": []
            },
            "contract": {
                "goal": task_description,
                "requires": [],
                "produces": [],
                "success_criteria": [],
                "preconditions": [],
                "postconditions": []
            },
            "automation": {
                "default_mode": "copilot",
                "agentic_allowed": True,
                "requires_human_decision": False,
                "requires_human_action": False,
                "risk_level": "medium"
            },
            "tool_binding_defaults": {},
            "information": {},
            "policy": {},
            "temporal": {},
            "escalation": {},
            "dependencies": {},
            "failure": {},
            "ui": {},
            "governance": {
                "status": "draft",
                "version": 1
            },
            "status": "draft"
        }
        
        return await self.create_task(task_data, created_by=created_by)
    
    # Task Grouping Methods
    
    async def create_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a task group."""
        group_key = group_data.get("group_key")
        if not group_key:
            group_key = self._generate_task_key(group_data.get("name", "unnamed_group"))
            group_data["group_key"] = group_key
        
        query = """
            INSERT INTO task_groups (group_key, name, description, parent_group_key, metadata)
            VALUES (:group_key, :name, :description, :parent_group_key, :metadata::jsonb)
            RETURNING *
        """
        
        values = {
            "group_key": group_key,
            "name": group_data["name"],
            "description": group_data.get("description"),
            "parent_group_key": group_data.get("parent_group_key"),
            "metadata": json.dumps(group_data.get("metadata", {}))
        }
        
        result = await database.fetch_one(query=query, values=values)
        return dict(result)
    
    async def add_task_to_group(self, task_key: str, group_key: str, display_order: int = 0) -> bool:
        """Add task to group."""
        query = """
            INSERT INTO task_group_memberships (task_key, group_key, display_order)
            VALUES (:task_key, :group_key, :display_order)
            ON CONFLICT (task_key, group_key) DO UPDATE SET display_order = :display_order
        """
        
        await database.execute(query=query, values={
            "task_key": task_key,
            "group_key": group_key,
            "display_order": display_order
        })
        return True
    
    async def remove_task_from_group(self, task_key: str, group_key: str) -> bool:
        """Remove task from group."""
        query = "DELETE FROM task_group_memberships WHERE task_key = :task_key AND group_key = :group_key"
        await database.execute(query=query, values={"task_key": task_key, "group_key": group_key})
        return True
    
    async def get_tasks_by_group(self, group_key: str) -> List[Dict[str, Any]]:
        """Get tasks in a group."""
        query = """
            SELECT t.*
            FROM task_catalog t
            INNER JOIN task_group_memberships tgm ON t.task_key = tgm.task_key
            WHERE tgm.group_key = :group_key
            ORDER BY tgm.display_order, t.name
        """
        
        results = await database.fetch_all(query=query, values={"group_key": group_key})
        return [self._task_row_to_dict(row) for row in results]
    
    async def get_group_hierarchy(self) -> Dict[str, Any]:
        """Get group hierarchy."""
        query = "SELECT * FROM task_groups ORDER BY name"
        groups = await database.fetch_all(query=query)
        
        # Build hierarchy
        group_dict = {}
        for group in groups:
            group_dict[group["group_key"]] = dict(group)
            group_dict[group["group_key"]]["tasks"] = []
        
        # Add tasks to groups
        for group_key in group_dict:
            tasks = await self.get_tasks_by_group(group_key)
            group_dict[group_key]["tasks"] = tasks
        
        return group_dict
    
    # Helper Methods
    
    def _generate_task_key(self, name: str) -> str:
        """
        Generate a stable task_key from a name (no timestamp).
        Same description = same key = reusable task.
        """
        # Convert to lowercase, replace spaces and special chars with underscores
        key = re.sub(r'[^a-z0-9_]+', '_', name.lower().strip())
        # Remove multiple underscores
        key = re.sub(r'_+', '_', key)
        # Remove leading/trailing underscores
        key = key.strip('_')
        # Ensure it starts with a letter
        if key and key[0].isdigit():
            key = f"task_{key}"
        # Ensure it's not empty
        if not key:
            key = "unnamed_task"
        # Truncate to reasonable length (keep first 100 chars to avoid too long keys)
        if len(key) > 100:
            key = key[:100]
        # NO timestamp - stable keys for reusable tasks
        return key
    
    def _infer_category_from_description(self, description: str) -> str:
        """Infer task category from description."""
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ["collect", "gather", "retrieve", "fetch", "get"]):
            return "collect"
        elif any(word in desc_lower for word in ["verify", "check", "validate", "confirm"]):
            return "verify"
        elif any(word in desc_lower for word in ["interpret", "analyze", "process", "parse"]):
            return "interpret"
        elif any(word in desc_lower for word in ["notify", "send", "email", "sms", "alert"]):
            return "notify"
        elif any(word in desc_lower for word in ["escalate", "raise", "elevate"]):
            return "escalate"
        elif any(word in desc_lower for word in ["decide", "choose", "select", "determine"]):
            return "decide"
        elif any(word in desc_lower for word in ["wait", "delay", "pause"]):
            return "wait"
        else:
            return "manual"
    
    async def _save_to_history(self, task: Dict[str, Any], changed_by: Optional[str] = None) -> None:
        """Save current task version to history."""
        query = """
            INSERT INTO task_catalog_history (task_key, version, task_data, changed_by)
            VALUES (:task_key, :version, CAST(:task_data AS jsonb), :changed_by)
            ON CONFLICT (task_key, version) DO NOTHING
        """
        
        await database.execute(query=query, values={
            "task_key": task["task_key"],
            "version": task["version"],
            "task_data": json.dumps(task),
            "changed_by": changed_by
        })
    
    def _task_row_to_dict(self, row: Any) -> Dict[str, Any]:
        """Convert database row to task dictionary."""
        if not row:
            return None
        
        task_dict = dict(row)
        
        # Parse JSONB fields
        jsonb_fields = [
            "classification", "contract", "automation", "tool_binding_defaults",
            "information", "policy", "temporal", "escalation", "dependencies",
            "failure", "ui", "governance"
        ]
        
        for field in jsonb_fields:
            task_dict[field] = parse_jsonb(task_dict.get(field, {}))
        
        # Convert UUID to string
        if "task_id" in task_dict and task_dict["task_id"]:
            task_dict["task_id"] = str(task_dict["task_id"])
        
        # Convert timestamps to ISO strings
        timestamp_fields = ["created_at_utc", "updated_at_utc", "deprecated_at_utc"]
        for field in timestamp_fields:
            if field in task_dict and task_dict[field]:
                if hasattr(task_dict[field], "isoformat"):
                    task_dict[field] = task_dict[field].isoformat()
        
        return task_dict


# Singleton instance
task_registry = TaskRegistry()

