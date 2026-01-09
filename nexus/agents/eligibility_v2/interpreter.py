"""
LLM Interpreter for Eligibility Agent V2

Interprets user input and updates CaseState. NEVER asks questions.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import date, datetime

from nexus.agents.eligibility_v2.models import (
    CaseState, UIEvent, LLMInterpretResponse, EventTense, CompletionStatus, CompletionStatusModel,
    CaseStateUpdateSuggestion
)
from nexus.agents.eligibility_v2.exceptions import LLMResponseValidationError
from nexus.services.eligibility_v2.llm_call_repository import LLMCallRepository
from nexus.modules.llm_gateway import LLMGateway
from nexus.core.json_parser import LLMResponseParser

logger = logging.getLogger("nexus.eligibility_v2.interpreter")


class EligibilityInterpreter:
    """LLM Interpreter agent. Updates CaseState from user input."""
    
    def __init__(self, llm_call_repository: LLMCallRepository = None):
        self.llm_call_repo = llm_call_repository or LLMCallRepository()
        self.llm_gateway = LLMGateway()
        self.json_parser = LLMResponseParser()
        
        # Load prompt template
        prompt_path = Path(__file__).parent.parent.parent / "configs" / "prompts" / "eligibility_v2_interpreter.json"
        try:
            with open(prompt_path, 'r') as f:
                self.prompt_config = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Prompt config not found at {prompt_path}, using defaults")
            self.prompt_config = {"system_prompt": "You are an eligibility interpretation agent."}
    
    async def interpret(
        self,
        case_state: CaseState,
        ui_event: UIEvent,
        case_pk: int,
        turn_id: int = None
    ) -> LLMInterpretResponse:
        """Interpret user input and update CaseState"""
        logger.info(f"Interpreting user input for case {case_pk}")
        
        # Build prompt
        prompt_text = self._build_prompt(case_state, ui_event)
        
        messages = [
            {"role": "system", "content": self.prompt_config.get("system_prompt", "")},
            {"role": "user", "content": prompt_text}
        ]
        
        # Call LLM
        try:
            llm_response = await self.llm_gateway.chat_completion(
                messages=messages,
                module_id="eligibility_v2",
                user_id="system"
            )
            
            response_text = llm_response.get("content", "{}")
            logger.debug(f"Raw LLM response: {response_text[:500]}")  # Log first 500 chars
            
            parse_result = self.json_parser.extract_json(response_text, normalize=False)
            
            if not parse_result.success or not parse_result.data:
                error_msg = parse_result.error or "Failed to parse JSON response"
                logger.error(f"Failed to parse LLM response: {error_msg}")
                logger.error(f"Raw response was: {response_text[:1000]}")  # Log first 1000 chars for debugging
                raise LLMResponseValidationError(f"JSON parse error: {error_msg}")
            
            response_data = parse_result.data
            logger.debug(f"Parsed response data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'not a dict'}")
            
            # Validate response
            interpret_response = self._validate_response(response_data)
            
            # Log LLM call
            await self.llm_call_repo.log_call(
                case_pk=case_pk,
                turn_id=turn_id,
                call_type="INTERPRETER",
                prompt_hash="",
                response_data=response_data
            )
            
            logger.info(f"Successfully interpreted user input for case {case_pk}")
            return interpret_response
            
        except Exception as e:
            logger.error(f"Failed to interpret user input: {e}", exc_info=True)
            raise
    
    def _build_prompt(self, case_state: CaseState, ui_event: UIEvent) -> str:
        """Build prompt for interpreter"""
        prompt = f"""Current CaseState:
{case_state.model_dump_json(indent=2)}

User Input:
Event Type: {ui_event.event_type}
Data: {json.dumps(ui_event.data, indent=2)}

CRITICAL: You are an INTERPRETER, not an updater. Your job is to EXTRACT information from user input and SUGGEST what should be updated. You do NOT directly update the CaseState.

CRITICAL: Preserve Eligibility Check Results:
- If eligibility_check.checked is True, you MUST NOT suggest changes to eligibility_truth fields
- These fields were set by a 270 transaction and should be preserved

CRITICAL: Extract and suggest updates for:
1. Patient demographics (first_name, last_name, date_of_birth, member_id, sex)
2. Health plan info (payer_name, payer_id, plan_name, product_type, contract_status)
3. Timing (dos_date)

CRITICAL: Extract product_type and contract_status from natural language:
- "MEDICAID" or "Medicaid" → health_plan_updates.product_type = "MEDICAID"
- "MEDICARE" or "Medicare" → health_plan_updates.product_type = "MEDICARE"
- "COMMERCIAL" or "Commercial" → health_plan_updates.product_type = "COMMERCIAL"
- "CONTRACTED" or "contracted" or "we are contracted" → health_plan_updates.contract_status = "CONTRACTED"
- "NON_CONTRACTED" or "non-contracted" → health_plan_updates.contract_status = "NON_CONTRACTED"
- "the contract is still active" → health_plan_updates.contract_status = "CONTRACTED"

CRITICAL: Date Extraction and Inference:
1. Extract dos_date from user input if explicitly mentioned:
   - "September 20, 2024" or "Sep 20, 2024" → timing_updates.dos_date = "2024-09-20"
   - "9/20/2024" → timing_updates.dos_date = "2024-09-20"
   - "it is 2026-02-01" → timing_updates.dos_date = "2026-02-01"
   - Always convert dates to ISO format (YYYY-MM-DD)

2. If dos_date is NOT in user input but timing.dos_date is null/missing:
   - INFER dos_date from timing.related_visits:
     * If there are scheduled/future visits → use the most future visit_date
     * If all visits are past → use the most recent visit_date
     * Priority: scheduled > completed > cancelled
   - This is CRITICAL: dos_date should NEVER remain null if visits are available
   - Suggest in timing_updates.dos_date

Return JSON with this structure:
{{
  "suggested_updates": {{
    "patient_updates": {{"first_name": "...", "date_of_birth": "YYYY-MM-DD", ...}},
    "health_plan_updates": {{"product_type": "COMMERCIAL", "contract_status": "CONTRACTED", ...}},
    "timing_updates": {{"dos_date": "YYYY-MM-DD"}},
    "other_updates": {{}}
  }},
  "completion": {{
    "status": "COMPLETE" | "INCOMPLETE" | "NEEDS_INPUT",
    "missing_fields": ["field1", "field2"]
  }},
  "reasoning": "Brief explanation of what you extracted and why"
}}
"""
        return prompt
    
    def _normalize_response_data(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize response data to handle common LLM response issues"""
        # Deep copy to avoid modifying original
        normalized = json.loads(json.dumps(response_data))
        
        # Normalize updated_case_state if present
        if "updated_case_state" in normalized and isinstance(normalized["updated_case_state"], dict):
            case_state = normalized["updated_case_state"]
            
            # Handle ineligible_explanation: if it's a string, set to None
            # (IneligibleExplanation expects an object with loss_timing, reinstate_possible, etc.)
            if "ineligible_explanation" in case_state:
                if isinstance(case_state["ineligible_explanation"], str):
                    logger.debug(f"Normalizing ineligible_explanation from string to None: {case_state['ineligible_explanation']}")
                    case_state["ineligible_explanation"] = None
                elif isinstance(case_state["ineligible_explanation"], dict):
                    # Validate it has the expected structure, otherwise set to None
                    expected_fields = {"loss_timing", "reinstate_possible", "reinstate_date"}
                    if not any(key in case_state["ineligible_explanation"] for key in expected_fields):
                        logger.debug("ineligible_explanation dict missing expected fields, setting to None")
                        case_state["ineligible_explanation"] = None
        
        return normalized
    
    def _validate_response(self, response_data: Dict[str, Any]) -> LLMInterpretResponse:
        """Validate response against schema"""
        try:
            # Normalize response data first
            response_data = self._normalize_response_data(response_data)
            
            # Check if response has the expected top-level structure
            if "suggested_updates" not in response_data or "completion" not in response_data:
                # Backward compatibility: check for old format
                if "updated_case_state" in response_data:
                    logger.warning("LLM returned old format (updated_case_state), converting to suggested_updates")
                    # Convert old format to new format
                    case_state = CaseState(**response_data["updated_case_state"])
                    
                    # Extract updates from case_state
                    suggested_updates = CaseStateUpdateSuggestion(
                        patient_updates={
                            k: v for k, v in case_state.patient.model_dump().items() 
                            if v is not None
                        },
                        health_plan_updates={
                            k: v.value if hasattr(v, 'value') else v 
                            for k, v in case_state.health_plan.model_dump().items() 
                            if v is not None and (not hasattr(v, 'value') or v.value != "UNKNOWN")
                        },
                        timing_updates={
                            k: v.isoformat() if isinstance(v, date) else (v.value if hasattr(v, 'value') else v)
                            for k, v in case_state.timing.model_dump().items() 
                            if v is not None and k != "related_visits"
                        }
                    )
                    response_data = {
                        "suggested_updates": suggested_updates.model_dump(),
                        "completion": response_data["completion"],
                        "reasoning": "Converted from old format"
                    }
                else:
                    logger.warning(f"LLM returned partial response. Got keys: {list(response_data.keys())}")
                    # Try to construct response from partial data
                    suggested_updates = CaseStateUpdateSuggestion()
                    completion = CompletionStatusModel(
                        status=CompletionStatus.INCOMPLETE,
                        missing_fields=[]
                    )
                    response_data = {
                        "suggested_updates": suggested_updates.model_dump(),
                        "completion": completion.model_dump(),
                        "reasoning": "Constructed from partial response"
                    }
            
            return LLMInterpretResponse(**response_data)
        except LLMResponseValidationError:
            raise
        except Exception as e:
            logger.error(f"Invalid LLM response: {e}")
            raise LLMResponseValidationError(f"Invalid response structure: {e}")
    
