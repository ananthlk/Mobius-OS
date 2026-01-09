"""
LLM Interpreter for Eligibility Agent V2

Interprets user input and updates CaseState. NEVER asks questions.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import date

from nexus.agents.eligibility_v2.models import (
    CaseState, UIEvent, LLMInterpretResponse, EventTense, CompletionStatus
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
            parse_result = self.json_parser.extract_json(response_text, normalize=False)
            
            if not parse_result.success or not parse_result.data:
                error_msg = parse_result.error or "Failed to parse JSON response"
                logger.error(f"Failed to parse LLM response: {error_msg}")
                raise LLMResponseValidationError(f"JSON parse error: {error_msg}")
            
            response_data = parse_result.data
            
            # Validate response
            interpret_response = self._validate_response(response_data)
            
            # Deterministically set event_tense if DOS provided
            interpret_response.updated_case_state = self._determine_event_tense(
                interpret_response.updated_case_state
            )
            
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

CRITICAL: Extract product_type and contract_status from natural language:
- "MEDICAID" or "Medicaid" → health_plan.product_type = "MEDICAID"
- "MEDICARE" or "Medicare" → health_plan.product_type = "MEDICARE"
- "COMMERCIAL" or "Commercial" → health_plan.product_type = "COMMERCIAL"
- "CONTRACTED" or "contracted" or "we are contracted" → health_plan.contract_status = "CONTRACTED"
- "NON_CONTRACTED" or "non-contracted" → health_plan.contract_status = "NON_CONTRACTED"
- "the contract is still active" → health_plan.contract_status = "CONTRACTED"

CRITICAL: Date Extraction Examples:
- "September 20, 2024" or "Sep 20, 2024" → timing.dos_date = "2024-09-20"
- "9/20/2024" → timing.dos_date = "2024-09-20"
- "it is 2026-02-01" → timing.dos_date = "2026-02-01"
- Always convert dates to ISO format (YYYY-MM-DD)
- After extracting dos_date, set timing.event_tense:
  * If dos_date is in the past (before today) → event_tense = "PAST"
  * If dos_date is in the future (after today) → event_tense = "FUTURE"
  * If dos_date is today → event_tense = "PAST"

Please update the CaseState with information from the user input.

Return JSON with this structure:
{{
  "updated_case_state": {{ /* Full CaseState object */ }},
  "completion": {{
    "status": "COMPLETE" | "INCOMPLETE" | "NEEDS_INPUT",
    "missing_fields": ["field1", "field2"]
  }}
}}
"""
        return prompt
    
    def _validate_response(self, response_data: Dict[str, Any]) -> LLMInterpretResponse:
        """Validate response against schema"""
        try:
            return LLMInterpretResponse(**response_data)
        except Exception as e:
            logger.error(f"Invalid LLM response: {e}")
            raise LLMResponseValidationError(f"Invalid response structure: {e}")
    
    def _determine_event_tense(self, case_state: CaseState) -> CaseState:
        """Deterministically set event_tense based on dos_date"""
        if case_state.timing.dos_date:
            today = date.today()
            if case_state.timing.dos_date <= today:
                case_state.timing.event_tense = EventTense.PAST
            else:
                case_state.timing.event_tense = EventTense.FUTURE
        return case_state
