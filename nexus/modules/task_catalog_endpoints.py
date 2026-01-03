"""
Task Catalog API Endpoints

REST API for managing the task catalog.
"""
import logging
import json
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from nexus.modules.task_registry import task_registry

logger = logging.getLogger("nexus.task_catalog")

router = APIRouter(prefix="/api/task-catalog", tags=["task-catalog"])


# Request/Response Models

class CreateTaskRequest(BaseModel):
    task_data: Dict[str, Any]


class UpdateTaskRequest(BaseModel):
    updates: Dict[str, Any]


class RegisterTaskFromConversationRequest(BaseModel):
    task_description: str
    context: Optional[Dict[str, Any]] = None


class CreateGroupRequest(BaseModel):
    group_data: Dict[str, Any]


class UpdateGroupRequest(BaseModel):
    updates: Dict[str, Any]


# Task Endpoints

@router.post("/tasks", status_code=201)
async def create_task(request: CreateTaskRequest, created_by: str = Query(default="system")):
    """Create a new task in the catalog."""
    try:
        task = await task_registry.create_task(request.task_data, created_by=created_by)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_key}")
async def get_task(task_key: str):
    """Get task by key."""
    task = await task_registry.get_task_by_key(task_key)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_key}' not found")
    return task


@router.patch("/tasks/{task_key}")
async def update_task(
    task_key: str,
    request: UpdateTaskRequest,
    updated_by: str = Query(default="system")
):
    """Update a task."""
    try:
        task = await task_registry.update_task(task_key, request.updates, updated_by=updated_by)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_key}")
async def delete_task(
    task_key: str,
    soft_delete: bool = Query(default=True)
):
    """Delete/deprecate a task."""
    try:
        success = await task_registry.delete_task(task_key, soft_delete=soft_delete)
        return {"success": success, "task_key": task_key}
    except Exception as e:
        logger.error(f"Error deleting task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None)
):
    """List tasks with optional filters."""
    filters = {}
    if status:
        filters["status"] = status
    if domain:
        filters["domain"] = domain
    if category:
        filters["category"] = category
    
    tasks = await task_registry.list_tasks(filters)
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/tasks/search")
async def search_tasks(request: Dict[str, Any]):
    """Search tasks by text."""
    query_text = request.get("query", "")
    filters = request.get("filters", {})
    
    if not query_text:
        raise HTTPException(status_code=400, detail="query field is required")
    
    tasks = await task_registry.search_tasks(query_text, filters)
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/tasks/register-from-conversation", status_code=201)
async def register_task_from_conversation(
    request: RegisterTaskFromConversationRequest,
    created_by: str = Query(default="system")
):
    """Register a task from conversation text."""
    try:
        task = await task_registry.register_task_from_conversation(
            request.task_description,
            context=request.context,
            created_by=created_by
        )
        return task
    except Exception as e:
        logger.error(f"Error registering task from conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_key}/validate")
async def validate_task(task_key: str):
    """Validate task schema."""
    task = await task_registry.get_task_by_key(task_key)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_key}' not found")
    
    from nexus.core.task_schema_validator import task_schema_validator
    is_valid, errors = task_schema_validator.validate_task_schema(task)
    
    return {
        "task_key": task_key,
        "is_valid": is_valid,
        "errors": errors
    }


@router.post("/tasks/validate-batch")
async def validate_batch_tasks(request: Dict[str, Any]):
    """Validate multiple tasks."""
    tasks_data = request.get("tasks", [])
    results = []
    
    from nexus.core.task_schema_validator import task_schema_validator
    
    for task_data in tasks_data:
        is_valid, errors = task_schema_validator.validate_task_schema(task_data)
        results.append({
            "task_key": task_data.get("task_key"),
            "is_valid": is_valid,
            "errors": errors
        })
    
    return {"results": results}


@router.get("/tasks/keys/{task_key}/exists")
async def check_task_exists(task_key: str):
    """Check if task exists."""
    task = await task_registry.get_task_by_key(task_key)
    return {"task_key": task_key, "exists": task is not None}


@router.get("/schema")
async def get_task_schema():
    """Get the task master schema for form generation."""
    try:
        # Load schema from config file (using same pattern as database.py)
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # nexus/
        schema_path = os.path.join(BASE_DIR, "configs", "task_master_schema.json")
        
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        return schema
    except FileNotFoundError:
        logger.error(f"Schema file not found at: {schema_path}")
        raise HTTPException(status_code=404, detail=f"Schema file not found at {schema_path}")
    except Exception as e:
        logger.error(f"Error loading schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Group Endpoints

@router.post("/groups", status_code=201)
async def create_group(request: CreateGroupRequest):
    """Create a task group."""
    try:
        group = await task_registry.create_group(request.group_data)
        return group
    except Exception as e:
        logger.error(f"Error creating group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/{group_key}")
async def get_group(group_key: str):
    """Get group with tasks."""
    # Get group details (would need to add get_group_by_key method to registry)
    tasks = await task_registry.get_tasks_by_group(group_key)
    return {
        "group_key": group_key,
        "tasks": tasks,
        "task_count": len(tasks)
    }


@router.get("/groups")
async def list_groups():
    """List all groups with hierarchy."""
    hierarchy = await task_registry.get_group_hierarchy()
    return {"groups": hierarchy}


@router.post("/groups/{group_key}/tasks/{task_key}")
async def add_task_to_group(
    group_key: str,
    task_key: str,
    display_order: int = Query(default=0)
):
    """Add task to group."""
    try:
        success = await task_registry.add_task_to_group(task_key, group_key, display_order)
        return {"success": success, "task_key": task_key, "group_key": group_key}
    except Exception as e:
        logger.error(f"Error adding task to group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/groups/{group_key}/tasks/{task_key}")
async def remove_task_from_group(group_key: str, task_key: str):
    """Remove task from group."""
    try:
        success = await task_registry.remove_task_from_group(task_key, group_key)
        return {"success": success, "task_key": task_key, "group_key": group_key}
    except Exception as e:
        logger.error(f"Error removing task from group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

