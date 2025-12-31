from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from nexus.workflows.registry import registry
from nexus.core.base_agent import AgentRecipe, AgentStep, NexusAgentFactory
from nexus.tools.crm.schedule_scanner import ScheduleScannerTool
from nexus.tools.crm.risk_calculator import RiskCalculatorTool

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
    Returns the schema of all available tools.
    Used by the Frontend Builder.
    """
    return [t.define_schema().dict() for t in AVAILABLE_TOOLS]

@router.get("/")
async def list_recipes():
    """
    Returns list of registered recipes.
    """
    return await registry.list_recipes() # ASYNC update

@router.get("/{name}")
async def get_recipe(name: str):
    recipe = await registry.get_recipe(name) # ASYNC update
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

class CreateRecipeRequest(BaseModel):
    name: str
    goal: str
    steps: Dict[str, Any] # simplified for now
    start_step_id: str

@router.post("/")
async def create_recipe(req: CreateRecipeRequest):
    """
    Endpoint for the Builder UI to save a new recipe.
    """
    # Convert raw dicts back to AgentStep objects
    steps = {}
    for step_id, step_data in req.steps.items():
        steps[step_id] = AgentStep(
            step_id=step_id, # Ensure ID is passed
            tool_name=step_data["tool_name"],
            description=step_data.get("description", ""),
            args_mapping=step_data.get("args_mapping", {}),
            transition_success=step_data.get("transition_success"),
            transition_fail=step_data.get("transition_fail")
        )

    new_recipe = AgentRecipe(
        name=req.name,
        goal=req.goal,
        steps=steps,
        start_step_id=req.start_step_id
    )
    
    await registry.register_recipe(new_recipe) # ASYNC update
    return {"status": "created", "name": req.name}

class RunRecipeRequest(BaseModel):
    initial_context: Dict[str, Any] = {}

@router.post("/run/{name}")
async def run_recipe_endpoint(name: str, req: RunRecipeRequest):
    """
    Executes a registered recipe by name.
    """
    recipe = await registry.get_recipe(name) # ASYNC update
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    factory = NexusAgentFactory(available_tools=AVAILABLE_TOOLS)
    
    try:
        result = await factory.run_recipe(recipe, initial_context=req.initial_context)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from nexus.brains.diagnosis import DiagnosisBrain
from nexus.modules.shaping_manager import shaping_manager

@router.post("/diagnose")
async def diagnose_problem(req: Dict[str, str]):
    """
    Analyzes a user problem and returns ranked solutions.
    Input: {"query": "..."}
    """
    brain = DiagnosisBrain()
    query = req.get("query", "")
    candidates = await brain.diagnose(query)
    return {"candidates": candidates}

# --- Shaping Session Endpoints (Stateful) ---

class StartShapingRequest(BaseModel):
    query: str
    user_id: str = "user_default" # Mock auth for now

class ChatRequest(BaseModel):
    message: str
    user_id: str = "user_default"

@router.post("/shaping/start")
async def start_shaping(req: StartShapingRequest):
    """
    Starts a new shaping session OR matches to existing workflows (Diagnosis).
    Returns session_id and candidates.
    """
    # 1. Start Session (Persistence)
    session_id = await shaping_manager.create_session(req.user_id, req.query)
    
    # 2. Diagnose (Logic)
    brain = DiagnosisBrain()
    candidates = await brain.diagnose(req.query)
    
    return {
        "session_id": session_id,
        "candidates": candidates,
        # Mock System Intro
        "system_intro": f"I've initialized session #{session_id}. Based on '{req.query}', here are some recommended workflows."
    }

@router.post("/shaping/{session_id}/chat")
async def shaping_chat(session_id: int, req: ChatRequest):
    """
    Handles chat interaction within a specific shaping session.
    """
    # 1. Log User Message
    await shaping_manager.append_message(session_id, "user", req.message)
    
    # 2. Simulate Brain Thinking (Mock LLM Call)
    # In reality, this is where we'd call: response = await gpt4.generate(history)
    mock_prompt = f"SYSTEM: You are a helpful assistant.\nUSER: {req.message}"
    mock_raw_output = {
        "choices": [{"text": f"I've noted: '{req.message}'. adjusting the parameters..."}],
        "usage": {"total_tokens": 42}
    }
    reply_text = mock_raw_output["choices"][0]["text"]
    
    # 3. Log the Trace (The "Black Box" Log)
    from nexus.modules.trace_manager import trace_manager
    trace_id = await trace_manager.log_trace(
        session_id=session_id,
        step_name="SHAPING_REPLY",
        prompt_snapshot=mock_prompt,
        raw_completion=mock_raw_output,
        model_metadata={"model": "gpt-4-mock", "latency": 150}
    )
    
    # 4. Log System Reply with Trace Link
    # We append the trace_id so the frontend (or admin UI) can link back to the raw log
    await shaping_manager.append_message(session_id, "system", reply_text)
    
    return {"reply": reply_text, "trace_id": trace_id}
