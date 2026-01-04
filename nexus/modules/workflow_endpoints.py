import logging
import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from nexus.conductors.workflows.orchestrator import orchestrator
from nexus.tools.crm.schedule_scanner import ScheduleScannerTool
from nexus.tools.crm.risk_calculator import RiskCalculatorTool
from nexus.modules.session_manager import session_manager
from nexus.modules.database import database
from nexus.modules.user_profile_events import track_workflow_interaction

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

@router.get("/trending-issues")
async def get_trending_issues(
    limit: int = Query(4, ge=1, le=10),
    days: int = Query(7, ge=1, le=30)
):
    """
    Get trending issues based on recent searches.
    Returns top N semantically similar queries from last N days.
    """
    from nexus.modules.trending_issues import get_trending_issues
    
    trending = await get_trending_issues(limit=limit, days=days)
    return {"trending_issues": trending}

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
async def shaping_chat(session_id: int, req: ChatRequest, background_tasks: BackgroundTasks):
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
        
        # Track profile interaction - get session details for context
        try:
            session_query = "SELECT consultant_strategy, workflow_name FROM shaping_sessions WHERE id = :session_id"
            session_row = await database.fetch_one(session_query, {"session_id": session_id})
            strategy = session_row.get("consultant_strategy") if session_row else None
            workflow_name = session_row.get("workflow_name") if session_row else None
        except Exception as e:
            logger.warning(f"Failed to get session details for profile tracking: {e}")
            strategy = None
            workflow_name = None
        
        # Extract assistant response from result
        assistant_response = ""
        if isinstance(result, dict):
            assistant_response = result.get("reply", result.get("message", result.get("content", str(result))))
        elif isinstance(result, str):
            assistant_response = result
        else:
            assistant_response = str(result)
        
        # Track workflow interaction
        try:
            await track_workflow_interaction(
                auth_id=req.user_id,
                user_message=req.message,
                assistant_response=assistant_response,
                session_id=session_id,
                workflow_name=workflow_name,
                strategy=strategy,
                background_tasks=background_tasks,
                metadata={"module": "workflow"}
            )
        except Exception as e:
            logger.warning(f"Failed to track workflow interaction: {e}", exc_info=True)
        
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

# --- Planning Phase Endpoints ---

class PlanningPhaseDecisionRequest(BaseModel):
    choice: str  # 'create_new', 'execute_existing', 'guide_me', or 'refine_answers'

class PlanningPhaseReviewRequest(BaseModel):
    selected_step_id: Optional[str] = None

@router.post("/shaping/{session_id}/planning-phase/decision")
async def planning_phase_decision(session_id: int, req: PlanningPhaseDecisionRequest):
    """
    Handle planning phase decision.
    Supports: 'create_new', 'execute_existing', 'guide_me', 'refine_answers'
    """
    from nexus.brains.planning_phase import planning_phase_brain
    
    logger.info(f"[PLANNING_PHASE_DECISION] Received request: session_id={session_id}, choice={req.choice}")
    
    try:
        result = await planning_phase_brain.handle_build_reuse_decision(
            session_id=session_id,
            choice=req.choice
        )
        logger.info(f"[PLANNING_PHASE_DECISION] Success: {result}")
        return result
    except Exception as e:
        logger.error(f"[PLANNING_PHASE_DECISION] Failed to handle planning phase decision: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shaping/{session_id}/planning-phase/compute")
async def planning_phase_compute(session_id: int):
    """
    Run system computation to analyze plan and detect ambiguous/missing info steps.
    """
    from nexus.brains.planning_phase import planning_phase_brain
    
    try:
        result = await planning_phase_brain.compute_plan_analysis(session_id)
        return result
    except Exception as e:
        logger.error(f"Failed to compute plan analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shaping/{session_id}/planning-phase/overview")
async def planning_phase_overview(session_id: int):
    """
    Get generic overview of the plan.
    """
    from nexus.brains.planning_phase import planning_phase_brain
    
    try:
        result = await planning_phase_brain.generate_plan_overview(session_id)
        return result
    except Exception as e:
        logger.error(f"Failed to generate plan overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shaping/{session_id}/planning-phase/options")
async def planning_phase_options(session_id: int):
    """
    Get conditional options based on card status.
    """
    from nexus.brains.planning_phase import planning_phase_brain
    
    try:
        result = await planning_phase_brain.get_planning_options(session_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get planning options: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shaping/{session_id}/planning-phase/approve")
async def planning_phase_approve(session_id: int):
    """
    Approve the plan.
    """
    from nexus.brains.planning_phase import planning_phase_brain
    
    try:
        result = await planning_phase_brain.handle_approve(session_id)
        return result
    except Exception as e:
        logger.error(f"Failed to approve plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shaping/{session_id}/planning-phase/review")
async def planning_phase_review(session_id: int, req: PlanningPhaseReviewRequest):
    """
    Enter review mode for a specific step or auto-select first problematic step.
    """
    from nexus.brains.planning_phase import planning_phase_brain
    
    try:
        result = await planning_phase_brain.handle_review_plan(
            session_id=session_id,
            selected_step_id=req.selected_step_id
        )
        return result
    except Exception as e:
        logger.error(f"Failed to enter review mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shaping/{session_id}/planning-phase/cancel")
async def planning_phase_cancel(session_id: int):
    """
    Cancel planning phase and return to gate phase.
    """
    from nexus.brains.planning_phase import planning_phase_brain
    
    try:
        result = await planning_phase_brain.handle_cancel(session_id)
        return result
    except Exception as e:
        logger.error(f"Failed to cancel planning phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Template Management Endpoints (Reusable)
# ============================================================================

@router.post("/templates/eligibility")
async def save_eligibility_template(
    template: Dict[str, Any],
    user_id: str = "user_123"
):
    """
    Save an eligibility plan template from Live Builder.
    
    Body:
    {
        "template_key": "eligibility:insurance_billing:past_event",
        "name": "Insurance Billing - Past Event",
        "description": "Template for billing past events",
        "template_config": {
            "phases": [...],
            "gate_mapping": {...}
        },
        "match_pattern": {
            "gates": {
                "2_use_case": "insurance_billing_past_event"
            }
        }
    }
    """
    from nexus.templates.template_manager import eligibility_template_manager
    from nexus.core.tree_structure_manager import TreePath
    
    # Parse template key or build from components
    if ":" in template.get("template_key", ""):
        path = TreePath.from_key(template["template_key"])
    else:
        path = TreePath(
            module=template.get("module", "workflow"),
            domain=template.get("domain", "eligibility"),
            strategy=template.get("strategy", "TABULA_RASA"),
            step=template.get("step", "template")
        )
    
    template_id = await eligibility_template_manager.save_template(
        path=path,
        name=template["name"],
        template_config=template["template_config"],
        match_pattern=template.get("match_pattern", {}),
        description=template.get("description"),
        user_id=user_id
    )
    
    return {
        "success": True,
        "template_id": template_id,
        "template_key": template.get("template_key") or path.to_key()
    }

@router.get("/templates/eligibility")
async def list_eligibility_templates():
    """
    List all active eligibility templates.
    """
    from nexus.templates.template_manager import eligibility_template_manager
    from nexus.core.tree_structure_manager import TreePath
    
    # Get templates for eligibility domain
    path = TreePath(
        module="workflow",
        domain="eligibility",
        strategy="TABULA_RASA",
        step="template"
    )
    
    templates = await eligibility_template_manager.list_templates(path)
    return templates

@router.get("/templates/eligibility/{template_key:path}")
async def get_eligibility_template(template_key: str):
    """
    Get a specific template by key.
    """
    from nexus.templates.template_manager import eligibility_template_manager
    from nexus.core.tree_structure_manager import TreePath
    
    try:
        path = TreePath.from_key(template_key)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid template key format: {template_key}")
    
    template = await eligibility_template_manager.get_template(path)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

# ============================================================================
# Plan State Management Endpoints (Reusable)
# ============================================================================

@router.post("/plans/{plan_id}/approve")
async def approve_plan(plan_id: int, user_id: str = "user_123"):
    """
    Approve a plan (DRAFT -> USER_APPROVED).
    """
    from nexus.core.plan_state_manager import plan_state_manager
    from nexus.core.plan_models import PlanStatus
    
    await plan_state_manager.update_plan_status(
        plan_id=plan_id,
        new_status=PlanStatus.USER_APPROVED,
        user_id=user_id
    )
    return {"success": True, "status": "user_approved"}

@router.post("/plans/{plan_id}/steps/{step_id}/enhance")
async def enhance_step(
    plan_id: int,
    step_id: str,
    enhancement: Dict[str, Any],
    user_id: str = "user_123"
):
    """
    Enhance a step with tool definition.
    
    Body:
    {
        "tool": {
            "tool_name": "check_eligibility_direct",
            "inputs": {"patient_id": "{{gate_state...}}"},
            "outputs": {"eligibility_status": "..."}
        },
        "reason": "Agent determined best tool for this step"
    }
    """
    from nexus.core.plan_state_manager import plan_state_manager
    from nexus.core.plan_models import ToolDefinition
    
    tool = ToolDefinition(**enhancement["tool"])
    
    await plan_state_manager.enhance_step_with_tool(
        plan_id=plan_id,
        step_id=step_id,
        tool=tool,
        enhanced_by=user_id,
        enhanced_by_type="agent",
        reason=enhancement.get("reason")
    )
    
    return {"success": True}

@router.post("/plans/{plan_id}/steps/{step_id}/map-inputs")
async def map_step_inputs(
    plan_id: int,
    step_id: str,
    input_mapping: Dict[str, str],
    user_id: str = "user_123"
):
    """
    Map step inputs to data sources.
    
    Body:
    {
        "patient_id": "{{gate_state.gates.1_patient_info.patient_id}}",
        "dob": "{{gate_state.gates.1_patient_info.dob}}"
    }
    """
    from nexus.core.plan_state_manager import plan_state_manager
    
    await plan_state_manager.map_step_inputs(
        plan_id=plan_id,
        step_id=step_id,
        input_mapping=input_mapping,
        mapped_by=user_id
    )
    
    return {"success": True}

@router.get("/plans/{plan_id}")
async def get_plan_with_state(plan_id: int):
    """
    Get plan with full state metadata.
    """
    from nexus.modules.database import database
    from nexus.modules.database import parse_jsonb
    
    query = """
        SELECT p.*, 
               json_agg(
                   json_build_object(
                       'id', ph.phase_id,
                       'name', ph.phase_name,
                       'status', ph.status,
                       'steps', (
                           SELECT json_agg(
                               json_build_object(
                                   'id', s.step_id,
                                   'description', s.description,
                                   'status', s.status,
                                   'tool', s.tool_definition,
                                   'metadata', s.metadata
                               )
                           )
                           FROM workflow_plan_steps s
                           WHERE s.phase_id = ph.id
                           ORDER BY s.execution_order
                       )
                   )
               ) FILTER (WHERE ph.id IS NOT NULL) as phases
        FROM workflow_plans p
        LEFT JOIN workflow_plan_phases ph ON ph.plan_id = p.id
        WHERE p.id = :plan_id
        GROUP BY p.id
    """
    
    row = await database.fetch_one(query, {"plan_id": plan_id})
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    result = dict(row)
    if result.get("plan_structure"):
        result["plan_structure"] = parse_jsonb(result["plan_structure"])
    if result.get("metadata"):
        result["metadata"] = parse_jsonb(result["metadata"])
    
    return result
