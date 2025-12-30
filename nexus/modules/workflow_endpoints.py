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
