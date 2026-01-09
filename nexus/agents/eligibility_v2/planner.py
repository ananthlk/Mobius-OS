"""
Eligibility Planner

Generates next questions and improvement plan.
"""
import logging
import json
from pathlib import Path
from nexus.agents.eligibility_v2.models import (
    CaseState, ScoreState, LLMPlanResponse, CompletionStatus, CompletionStatusModel, NextQuestion, ImprovementAction
)
from nexus.services.eligibility_v2.llm_call_repository import LLMCallRepository
from nexus.modules.llm_gateway import LLMGateway
from nexus.core.json_parser import LLMResponseParser

logger = logging.getLogger("nexus.eligibility_v2.planner")


class EligibilityPlanner:
    """Planner for generating questions and improvement plan"""
    
    def __init__(self):
        self.llm_call_repo = LLMCallRepository()
        self.llm_gateway = LLMGateway()
        self.json_parser = LLMResponseParser()
        
        # Load prompt config
        prompt_path = Path(__file__).parent.parent.parent / "configs" / "prompts" / "eligibility_v2_planner.json"
        try:
            with open(prompt_path, 'r') as f:
                self.prompt_config = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Prompt config not found at {prompt_path}")
            self.prompt_config = {"system_prompt": "You are an eligibility planning agent."}
    
    async def plan(
        self,
        case_state: CaseState,
        score_state: ScoreState,
        completion_status: CompletionStatusModel
    ) -> LLMPlanResponse:
        """Generate plan with next questions and improvement plan"""
        logger.info("Generating plan")
        
        # Build prompt
        prompt_text = self._build_prompt(case_state, score_state, completion_status)
        
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
                raise Exception(f"JSON parse error: {error_msg}")
            
            response_data = parse_result.data
            
            # Normalize response data - handle when LLM returns strings instead of objects
            response_data = self._normalize_response_data(response_data)
            
            # Validate and return
            plan_response = LLMPlanResponse(**response_data)
            
            # Validate that questions were generated if fields are missing
            missing_fields = completion_status.missing_fields
            if missing_fields and len(plan_response.next_questions) == 0:
                logger.warning(f"Missing fields detected but no questions generated: {missing_fields}")
                # Generate fallback questions for missing fields
                plan_response.next_questions = self._generate_fallback_questions(missing_fields)
                plan_response.improvement_plan = self._generate_fallback_improvements(missing_fields) if not plan_response.improvement_plan else plan_response.improvement_plan
                # Update presentation summary to be more specific
                if not plan_response.presentation_summary or "information" in plan_response.presentation_summary.lower():
                    plan_response.presentation_summary = self._generate_fallback_summary(missing_fields)
            
            logger.info(f"Generated plan with {len(plan_response.next_questions)} questions and {len(plan_response.improvement_plan)} improvements")
            return plan_response
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}", exc_info=True)
            # Return empty plan on error
            return LLMPlanResponse(
                next_questions=[],
                improvement_plan=[],
                presentation_summary="I need more information to help you with this eligibility check."
            )
    
    def _normalize_response_data(self, data: dict) -> dict:
        """Normalize LLM response data - convert strings to objects if needed"""
        from typing import List, Dict, Any
        
        normalized = data.copy()
        
        # Normalize next_questions - if items are strings, convert to objects
        if "next_questions" in normalized:
            questions = normalized["next_questions"]
            if questions:
                if isinstance(questions[0], str):
                    normalized["next_questions"] = [
                        {
                            "id": f"q_{i+1}",
                            "text": q,
                            "answer_format": "FREE_TEXT",
                            "options": [],
                            "fills": [],
                            "improves": ["COMPLETENESS"],
                            "why": "Required to gather missing information"
                        }
                        for i, q in enumerate(questions)
                    ]
                else:
                    # Normalize enum values in improves field
                    normalized_questions = []
                    for q in questions:
                        if isinstance(q, dict):
                            if "improves" in q and isinstance(q["improves"], list):
                                # Map invalid enum values to valid ones
                                valid_improves = []
                                for imp in q["improves"]:
                                    if imp in ["CONFIDENCE", "PROBABILITY", "COMPLETENESS"]:
                                        valid_improves.append(imp)
                                    elif imp in ["EVIDENCE_STRENGTH", "EVIDENCE"]:
                                        valid_improves.append("CONFIDENCE")  # Map to closest valid value
                                    else:
                                        valid_improves.append("COMPLETENESS")  # Default
                                q["improves"] = valid_improves
                            normalized_questions.append(q)
                        else:
                            normalized_questions.append(q)
                    normalized["next_questions"] = normalized_questions
        
        # Normalize improvement_plan - if items are strings, convert to objects
        if "improvement_plan" in normalized:
            plan = normalized["improvement_plan"]
            if plan:
                if isinstance(plan[0], str):
                    normalized["improvement_plan"] = [
                        {
                            "action_id": f"action_{i+1}",
                            "description": a,
                            "requires": "USER_INPUT",
                            "expected_effect": "RESOLVE_COMPLETENESS",
                            "priority": i + 1
                        }
                        for i, a in enumerate(plan)
                    ]
                else:
                    # Normalize enum values in expected_effect field
                    normalized_plan = []
                    for a in plan:
                        if isinstance(a, dict):
                            if "expected_effect" in a:
                                effect = a["expected_effect"]
                                if effect not in ["INCREASE_CONFIDENCE", "INCREASE_PROBABILITY", "RESOLVE_COMPLETENESS"]:
                                    if effect in ["INCREASE_EVIDENCE_STRENGTH", "EVIDENCE_STRENGTH"]:
                                        a["expected_effect"] = "INCREASE_CONFIDENCE"  # Map to closest valid value
                                    else:
                                        a["expected_effect"] = "RESOLVE_COMPLETENESS"  # Default
                            normalized_plan.append(a)
                        else:
                            normalized_plan.append(a)
                    normalized["improvement_plan"] = normalized_plan
        
        return normalized
    
    def _generate_fallback_questions(self, missing_fields: list) -> list:
        """Generate fallback questions for missing fields"""
        from nexus.agents.eligibility_v2.models import NextQuestion
        
        questions = []
        field_prompts = {
            "payer_name": "What is the insurance payer or insurance company name?",
            "payer_id": "What is the payer ID?",
            "plan_name": "What is the plan name?",
            "date_of_birth": "What is the patient's date of birth?",
            "sex": "What is the patient's sex (M/F/Other)?",
            "member_id": "What is the member ID?",
            "dos_date": "What is the date of service?",
            "first_name": "What is the patient's first name?",
            "last_name": "What is the patient's last name?",
        }
        
        for i, field in enumerate(missing_fields[:5], 1):  # Limit to 5 questions
            question_text = field_prompts.get(field, f"What is the {field.replace('_', ' ')}?")
            questions.append(NextQuestion(
                id=f"q_{i}",
                text=question_text,
                answer_format="FREE_TEXT",
                options=[],
                fills=[field],
                improves=["COMPLETENESS"],
                why=f"Required field: {field}"
            ))
        
        return questions
    
    def _generate_fallback_improvements(self, missing_fields: list) -> list:
        """Generate fallback improvement actions for missing fields"""
        from nexus.agents.eligibility_v2.models import ImprovementAction
        
        improvements = []
        for i, field in enumerate(missing_fields[:5], 1):  # Limit to 5 actions
            improvements.append(ImprovementAction(
                action_id=f"action_{i}",
                description=f"Collect {field.replace('_', ' ')} from user",
                requires="USER_INPUT",
                expected_effect="RESOLVE_COMPLETENESS",
                priority=i,
                why=f"Required for eligibility check: {field}"
            ))
        
        return improvements
    
    def _generate_fallback_summary(self, missing_fields: list) -> str:
        """Generate fallback presentation summary"""
        if not missing_fields:
            return "I have all the information needed to proceed with the eligibility check."
        
        field_names = [f.replace('_', ' ') for f in missing_fields[:5]]
        if len(missing_fields) > 5:
            field_names.append("and more")
        
        fields_text = ', '.join(field_names)
        return f"To complete the eligibility check, I need the following information: {fields_text}. Please provide these details so I can proceed."
    
    def _build_prompt(self, case_state: CaseState, score_state: ScoreState, completion_status: CompletionStatusModel) -> str:
        """Build prompt for planner"""
        missing_fields = completion_status.missing_fields
        
        missing_fields_text = ', '.join(missing_fields) if missing_fields else 'None'
        critical_instruction = ""
        if missing_fields:
            critical_instruction = f"""

CRITICAL: The following fields are MISSING and MUST be collected: {missing_fields_text}
You MUST generate at least one question for each missing field. Do NOT return empty arrays.
Questions should directly ask for the missing information in a natural, conversational way."""
        else:
            # When all fields are complete, generate a summary of the results
            critical_instruction = """

CRITICAL: All required fields are complete. Generate a presentation_summary that:
1. Acknowledges the user's input and thanks them for providing the information
2. Provides the eligibility probability and status (from score_state.base_probability and eligibility_truth.status)
3. Summarizes the key findings from the eligibility check
4. Offers next steps or recommendations based on the results
The presentation_summary should be informative and helpful, not empty or generic. It should be a complete, conversational response that the user can read."""
        
        prompt = f"""Current CaseState:
{case_state.model_dump_json(indent=2)}

Current ScoreState:
{score_state.model_dump_json(indent=2)}

Missing Fields: {missing_fields_text}{critical_instruction}

Generate next questions and improvement plan. Return JSON with:
{{
  "next_questions": [
    {{
      "id": "q1",
      "text": "Question text",
      "answer_format": "FREE_TEXT",
      "options": [],
      "fills": [],
      "improves": ["COMPLETENESS"],
      "why": "Why this question is needed"
    }}
  ],
  "improvement_plan": [
    {{
      "action_id": "action1",
      "description": "Action description",
      "requires": "USER_INPUT",
      "expected_effect": "RESOLVE_COMPLETENESS",
      "priority": 1
    }}
  ],
  "presentation_summary": "Summary text explaining what information is needed and why, OR if all fields are complete, provide the eligibility results and recommendations"
}}

IMPORTANT: 
- next_questions and improvement_plan must be arrays of objects, not strings.
- If there are missing fields, you MUST generate questions to collect them.
- The presentation_summary should ALWAYS be meaningful and informative.
- If all fields are complete, the presentation_summary should provide the eligibility results and acknowledge the user's input.
- Do NOT return empty arrays when fields are missing.
- Do NOT return empty or generic presentation_summary when fields are complete.
"""
        return prompt
