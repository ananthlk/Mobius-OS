import logging
import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from nexus.conductors.workflows.orchestrator import orchestrator
from nexus.tools.crm.schedule_scanner import ScheduleScannerTool
from nexus.tools.crm.risk_calculator import RiskCalculatorTool
from nexus.modules.session_manager import session_manager

# Setup Logger
logger = logging.getLogger("nexus.workflows")

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# --- Init Registry with Available Tools ---
# In a real app, this might be dynamic plugin loading
AVAILABLE_TOOLS = [
    ScheduleScannerTool(),
    RiskCalculatorTool()
]

@router.get("/tools")
async def list_tools():
    """
    Returns the schema of all available tools from the tool library.
    Used by the Frontend Builder.
    """
    from nexus.tools.library.registry import tool_registry
    
    # Get tools from database
    db_tools = await tool_registry.get_all_active_tools()
    
    # Convert to schema format for frontend
    tools_schema = []
    for tool_data in db_tools:
        # Build schema dict from database tool
        schema = {
            "name": tool_data["name"],
            "description": tool_data["description"],
            "parameters": {},
            "execution_conditions": tool_data.get("execution_conditions", []),
            "supports_conditional_execution": tool_data.get("supports_conditional_execution", False)
        }
        
        # Add parameters from normalized table
        if tool_data.get("parameters"):
            for param in tool_data["parameters"]:
                schema["parameters"][param["parameter_name"]] = f"{param['parameter_type']} ({param.get('description', '')})"
        
        tools_schema.append(schema)
    
    # Also include hardcoded tools for backward compatibility
    hardcoded_schemas = [t.define_schema().dict() for t in AVAILABLE_TOOLS]
    tools_schema.extend(hardcoded_schemas)
    
    return tools_schema

@router.get("/")
async def list_recipes():
    """
    Returns list of registered recipes.
    """
    try:
        return await orchestrator.list_recipes()
    except Exception as e:
        logger.error(f"Failed to list recipes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}")
async def get_recipe(name: str):
    """
    Get a recipe by name.
    """
    try:
        recipe = await orchestrator.get_recipe(name)
        if "error" in recipe:
            raise HTTPException(status_code=404, detail=recipe["error"])
        return recipe
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recipe {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class CreateRecipeRequest(BaseModel):
    name: str
    goal: str
    steps: Dict[str, Any] # simplified for now
    start_step_id: str

# --- Shaping Session Schemas ---

class StartShapingRequest(BaseModel):
    query: str
    user_id: str = "user_default" # Mock auth for now

class ChatRequest(BaseModel):
    message: str
    user_id: str = "user_default"

class UpdateDraftPlanRequest(BaseModel):
    problem_statement: Optional[str] = None
    name: Optional[str] = None
    goal: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None  # Full steps array (for reordering)

# --- Shaping Session Endpoints ---

@router.post("/shaping/start")
async def start_shaping(req: StartShapingRequest):
    """
    Starts a new shaping session OR matches to existing workflows (Diagnosis).
    Returns session_id and candidates.
    """
    # Validation
    if not req.query or not req.user_id:
        raise HTTPException(status_code=400, detail="Missing required fields: query and user_id")
    
    # Delegate to orchestrator
    try:
        result = await orchestrator.start_shaping_session(
            user_id=req.user_id,
            query=req.query
        )
        return result
    except Exception as e:
        logger.error(f"Failed to start shaping session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- WebSocket Endpoint (Live Stream) ---
@router.websocket("/shaping/{session_id}/ws")
async def websocket_shaping_stream(websocket: WebSocket, session_id: int):
    """
    Connects to the Live Event Stream for a given session.
    Path A (UI Hot Path).
    """
    await session_manager.connect(session_id, websocket)
    try:
        while True:
            # Keepalive / Client messages
            # For now we just listen, mainly we are pushing data OUT.
            data = await websocket.receive_text()
            # echo or heartbeat logic could go here
    except WebSocketDisconnect:
        session_manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        session_manager.disconnect(session_id, websocket)

@router.get("/shaping/{session_id}")
async def get_shaping_session(session_id: int):
    """
    Returns the full session state (Scanning for updates).
    """
    try:
        session = await orchestrator.get_session_state(session_id)
        if "error" in session:
            raise HTTPException(status_code=404, detail=session["error"])
        
        # JSON field handling for Pydantic/FastAPI auto-serialization
        if isinstance(session.get("transcript"), str):
            session["transcript"] = json.loads(session["transcript"])
        if isinstance(session.get("draft_plan"), str):
            session["draft_plan"] = json.loads(session["draft_plan"])
        if isinstance(session.get("rag_citations"), str):
            session["rag_citations"] = json.loads(session["rag_citations"])
        
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shaping/{session_id}/journey-state")
async def get_journey_state_endpoint(session_id: int):
    """
    Get journey state for a session.
    Can be used by frontend for direct access without full session data.
    """
    from nexus.modules.journey_state import journey_state_manager
    
    journey_state = await journey_state_manager.get_journey_state(session_id)
    
    if not journey_state:
        raise HTTPException(status_code=404, detail="Journey state not found")
    
    return journey_state

@router.post("/shaping/{session_id}/chat")
async def shaping_chat(session_id: int, req: ChatRequest):
    """
    Handles chat interaction within a specific shaping session.
    """
    # Validation
    if not req.message:
        raise HTTPException(status_code=400, detail="Message required")
    
    # Delegate to orchestrator
    try:
        result = await orchestrator.handle_chat_message(
            session_id=session_id,
            message=req.message,
            user_id=req.user_id
        )
        return result
    except Exception as e:
        logger.error(f"Failed to handle chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/shaping/{session_id}/draft-plan")
async def update_draft_plan(session_id: int, req: UpdateDraftPlanRequest):
    """
    Update draft plan for a shaping session.
    Allows CRUD operations on steps.
    """
    try:
        result = await orchestrator.update_draft_plan(
            session_id=session_id,
            updates={
                "problem_statement": req.problem_statement,
                "name": req.name,
                "goal": req.goal,
                "steps": req.steps
            }
        )
        return result
    except Exception as e:
        logger.error(f"Failed to update draft plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_recipe(req: CreateRecipeRequest):
    """
    Endpoint for the Builder UI to save a new recipe.
    """
    # Validation
    if not req.name or not req.goal or not req.start_step_id:
        raise HTTPException(status_code=400, detail="Missing required fields: name, goal, start_step_id")
    
    # Delegate to orchestrator
    try:
        result = await orchestrator.create_recipe({
            "name": req.name,
            "goal": req.goal,
            "steps": req.steps,
            "start_step_id": req.start_step_id
        })
        return result
    except Exception as e:
        logger.error(f"Failed to create recipe: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class RunRecipeRequest(BaseModel):
    initial_context: Dict[str, Any] = {}

@router.post("/run/{name}")
async def run_recipe_endpoint(name: str, req: RunRecipeRequest):
    """
    Executes a registered recipe by name.
    """
    # Validation
    if not name:
        raise HTTPException(status_code=400, detail="Recipe name required")
    
    # Delegate to orchestrator
    try:
        result = await orchestrator.execute_workflow(
            recipe_name=name,
            initial_context=req.initial_context,
            session_id=None  # Can be extended to accept session_id from request
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute workflow {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diagnose")
async def diagnose_problem(req: Dict[str, str]):
    """
    Analyzes a user problem and returns ranked solutions.
    Input: {"query": "..."}
    """
    query = req.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    
    # Delegate to orchestrator (using a temporary session_id of 0 for standalone diagnosis)
    try:
        candidates = await orchestrator.analyze_existing_workflows(session_id=0, query=query)
        return {
            "candidates": [
                {
                    "recipe_name": c.recipe_name,
                    "goal": c.goal,
                    "match_score": c.match_score,
                    "missing_info": c.missing_info,
                    "reasoning": c.reasoning,
                    "origin": c.origin
                } for c in candidates
            ]
        }
    except Exception as e:
        logger.error(f"Failed to diagnose problem: {e}")
        raise HTTPException(status_code=500, detail=str(e))
