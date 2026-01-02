from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from nexus.modules.prompt_manager import prompt_manager
from nexus.modules.config_manager import config_manager
import logging
import json

logger = logging.getLogger("nexus.prompts")

router = APIRouter(prefix="/api/admin/prompts", tags=["prompts"])

# --- Pydantic Schemas ---

class PromptCreate(BaseModel):
    module_name: str
    domain: str
    mode: str
    step: str
    prompt_config: Dict[str, Any]
    description: Optional[str] = None

class PromptUpdate(BaseModel):
    prompt_config: Dict[str, Any]
    change_reason: Optional[str] = None

class PromptRefineRequest(BaseModel):
    situation: str
    requirements: str
    what_works: str
    what_doesnt_work: str
    user_id: Optional[str] = None

class PromptResponse(BaseModel):
    id: int
    prompt_key: str
    module_name: str
    domain: Optional[str]
    mode: Optional[str]
    step: Optional[str]
    version: int
    prompt_config: Dict[str, Any]
    description: Optional[str]
    created_at: str
    updated_at: Optional[str]
    created_by: Optional[str]

class PromptListResponse(BaseModel):
    id: int
    prompt_key: str
    module_name: str
    domain: Optional[str]
    mode: Optional[str]
    step: Optional[str]
    version: int
    description: Optional[str]
    created_at: str
    updated_at: Optional[str]

class PromptHistoryResponse(BaseModel):
    version: int
    prompt_config: Dict[str, Any]
    changed_by: Optional[str]
    change_reason: Optional[str]
    created_at: str

class PromptRefineResponse(BaseModel):
    refined_prompt: Dict[str, Any]
    reasoning: Optional[str] = None

# --- Endpoints ---

@router.get("", response_model=List[PromptListResponse])
async def list_prompts(
    module_name: Optional[str] = None,
    domain: Optional[str] = None,
    mode: Optional[str] = None,
    step: Optional[str] = None,
    active_only: bool = True
):
    """
    List all prompts with optional filtering.
    New structure: MODULE:DOMAIN:MODE:STEP
    """
    try:
        prompts = await prompt_manager.list_prompts(
            module_name=module_name,
            domain=domain,
            mode=mode,
            step=step,
            active_only=active_only
        )
        # Convert datetime objects to ISO format strings
        formatted_prompts = []
        for prompt in prompts:
            formatted_prompt = dict(prompt)
            if formatted_prompt.get("created_at"):
                formatted_prompt["created_at"] = formatted_prompt["created_at"].isoformat() if hasattr(formatted_prompt["created_at"], "isoformat") else str(formatted_prompt["created_at"])
            if formatted_prompt.get("updated_at"):
                formatted_prompt["updated_at"] = formatted_prompt["updated_at"].isoformat() if hasattr(formatted_prompt["updated_at"], "isoformat") else str(formatted_prompt["updated_at"])
            formatted_prompts.append(formatted_prompt)
        return formatted_prompts
    except Exception as e:
        logger.error(f"Failed to list prompts: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{prompt_key:path}", response_model=PromptResponse)
async def get_prompt(prompt_key: str):
    """
    Get a specific prompt by its key.
    Note: Uses :path to handle colons in prompt keys like 'workflow:TABULA_RASA'
    """
    try:
        # URL decode the prompt_key in case it was encoded
        from urllib.parse import unquote
        prompt_key = unquote(prompt_key)
        
        # Get full metadata from database (including prompt_config)
        from nexus.modules.database import database
        query = """
            SELECT id, prompt_key, module_name, domain, mode, step, version,
                   description, created_at, updated_at, created_by, prompt_config
            FROM prompt_templates
            WHERE prompt_key = :key AND is_active = true
            ORDER BY version DESC
            LIMIT 1
        """
        row = await database.fetch_one(query, {"key": prompt_key})
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_key} not found")
        
        # Convert to dict (database.fetch_one returns a Record which can be converted to dict)
        row_dict = dict(row)
        
        # Format datetime fields
        created_at_str = ""
        if row_dict.get("created_at"):
            created_at = row_dict["created_at"]
            created_at_str = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
        
        updated_at_str = None
        if row_dict.get("updated_at"):
            updated_at = row_dict["updated_at"]
            updated_at_str = updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at)
        
        # prompt_config from database (JSONB is returned as string by PostgreSQL)
        from nexus.modules.database import parse_jsonb
        prompt_config = parse_jsonb(row_dict.get("prompt_config"))
        
        if prompt_config is None:
            raise HTTPException(status_code=500, detail="prompt_config is missing")
        if not isinstance(prompt_config, dict):
            logger.error(f"prompt_config for {prompt_key} is not a valid dict: {type(prompt_config)}")
            raise HTTPException(status_code=500, detail="Invalid prompt_config format in database")
        # If it's already a dict, use it as-is
        
        return {
            "id": row_dict["id"],
            "prompt_key": row_dict["prompt_key"],
            "module_name": row_dict["module_name"],
            "domain": row_dict.get("domain"),
            "mode": row_dict.get("mode"),
            "step": row_dict.get("step"),
            "version": row_dict["version"],
            "prompt_config": prompt_config,  # Now guaranteed to be a dict
            "description": row_dict.get("description"),
            "created_at": created_at_str,
            "updated_at": updated_at_str,
            "created_by": row_dict.get("created_by")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prompt {prompt_key}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", status_code=201)
async def create_prompt(
    prompt: PromptCreate,
    x_user_id: str = Header("unknown", alias="X-User-ID"),
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """
    Create a new prompt template.
    """
    try:
        user_context = {
            "user_id": x_user_id,
            "session_id": x_session_id
        }
        
        prompt_id = await prompt_manager.create_prompt(
            module_name=prompt.module_name,
            domain=prompt.domain,
            mode=prompt.mode,
            step=prompt.step,
            prompt_config=prompt.prompt_config,
            description=prompt.description,
            user_context=user_context
        )
        
        return {"id": prompt_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{prompt_key:path}")
async def update_prompt(
    prompt_key: str,
    prompt_update: PromptUpdate,
    x_user_id: str = Header("unknown", alias="X-User-ID"),
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """
    Update a prompt (creates new version, archives old).
    """
    try:
        # URL decode the prompt_key in case it was encoded
        from urllib.parse import unquote
        prompt_key = unquote(prompt_key)
        
        user_context = {
            "user_id": x_user_id,
            "session_id": x_session_id
        }
        
        new_id = await prompt_manager.update_prompt(
            prompt_key=prompt_key,
            prompt_config=prompt_update.prompt_config,
            change_reason=prompt_update.change_reason,
            user_context=user_context
        )
        
        # Get the new version number
        from nexus.modules.database import database
        version_query = "SELECT version FROM prompt_templates WHERE id = :id"
        version = await database.fetch_val(version_query, {"id": new_id})
        
        return {"id": new_id, "status": "updated", "prompt_key": prompt_key, "version": version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update prompt {prompt_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{prompt_key:path}/history", response_model=List[PromptHistoryResponse])
async def get_prompt_history(prompt_key: str):
    """
    Get version history for a prompt.
    """
    try:
        # URL decode the prompt_key in case it was encoded
        from urllib.parse import unquote
        prompt_key = unquote(prompt_key)
        
        history = await prompt_manager.get_prompt_history(prompt_key)
        
        # Format response
        formatted_history = []
        for item in history:
            formatted_history.append({
                "version": item["version"],
                "prompt_config": item["prompt_config"],
                "changed_by": item.get("changed_by"),
                "change_reason": item.get("change_reason"),
                "created_at": item["created_at"].isoformat() if item.get("created_at") else ""
            })
        
        return formatted_history
    except Exception as e:
        logger.error(f"Failed to get history for {prompt_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{prompt_key:path}/refine", response_model=PromptRefineResponse)
async def refine_prompt(
    prompt_key: str,
    refine_request: PromptRefineRequest,
    x_user_id: str = Header("unknown", alias="X-User-ID"),
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """
    Use LLM to refine/improve a prompt based on feedback.
    """
    try:
        # URL decode the prompt_key in case it was encoded
        from urllib.parse import unquote
        prompt_key = unquote(prompt_key)
        
        # Get existing prompt - parse new key format: MODULE:DOMAIN:MODE:STEP
        parts = prompt_key.split(":")
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail=f"Invalid prompt_key format. Expected MODULE:DOMAIN:MODE:STEP, got: {prompt_key}")
        
        module_name = parts[0]
        domain = parts[1]
        mode = parts[2]
        step = parts[3]
        
        prompt_data = await prompt_manager.get_prompt(
            module_name=module_name,
            domain=domain,
            mode=mode,
            step=step
        )
        
        if not prompt_data:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_key} not found")
        
        existing_prompt = prompt_data["config"]
        
        # Build refinement prompt
        refinement_prompt = f"""You are a prompt engineering expert. Your task is to improve an existing prompt based on user feedback.

SITUATION:
{refine_request.situation}

REQUIREMENTS:
{refine_request.requirements}

WHAT'S WORKING:
{refine_request.what_works}

WHAT'S NOT WORKING:
{refine_request.what_doesnt_work}

CURRENT PROMPT STRUCTURE:
{json.dumps(existing_prompt, indent=2)}

INSTRUCTIONS:
1. Analyze the current prompt structure and identify areas for improvement
2. Address the issues mentioned in "WHAT'S NOT WORKING"
3. Preserve what's working well (from "WHAT'S WORKING")
4. Ensure the refined prompt meets the requirements
5. Return ONLY a valid JSON object matching the structure of the current prompt_config
6. Do not add any explanatory text, just return the JSON

Return the improved prompt_config as a JSON object:"""

        # Get model context for refinement
        user_id = refine_request.user_id or x_user_id
        model_context = await config_manager.resolve_app_context("workflow", user_id)
        
        # Call LLM service
        from nexus.modules.llm_service import llm_service
        refined_text = await llm_service.generate_text(
            prompt=refinement_prompt,
            system_instruction="You are a prompt engineering expert. Always return valid JSON matching the requested structure.",
            model_context=model_context,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 8192,
                "top_p": 0.95
            }
        )
        
        # Parse the refined prompt (may need to extract JSON from markdown code blocks)
        refined_json_str = refined_text.strip()
        
        # Remove markdown code blocks if present
        if refined_json_str.startswith("```"):
            lines = refined_json_str.split("\n")
            refined_json_str = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        
        try:
            refined_prompt_config = json.loads(refined_json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse refined prompt JSON: {e}")
            logger.error(f"Raw response: {refined_text}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM returned invalid JSON. Please try again. Error: {str(e)}"
            )
        
        return {
            "refined_prompt": refined_prompt_config,
            "reasoning": None  # Could extract reasoning if LLM provides it
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refine prompt {prompt_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

