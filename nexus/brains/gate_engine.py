"""
Gate Engine - Domain-agnostic gate execution engine.

Replaces ConsultantBrain with a config-driven approach for collecting
structured workflow requirements through gates.
"""

import logging
from typing import Dict, Any, Optional, Literal, Tuple, List
from datetime import datetime
from nexus.core.gate_models import (
    GateConfig,
    GateState,
    GateValue,
    StatusInfo,
    ConsultantResult,
    GateDecision,
    GateJsonParser,
    ParseResult,
    GateDecisionResult,
    ParseError
)
from nexus.core.memory_logger import MemoryLogger
from nexus.services.gate.prompt_builder import GatePromptBuilder
from nexus.services.gate.llm_service import GateLLMService
from nexus.engines.gate.completion_checker import GateCompletionChecker
from nexus.engines.gate.state_merger import GateStateMerger
from nexus.engines.gate.gate_selector import GateSelector

logger = logging.getLogger("nexus.gate_engine")


class GateEngine:
    """
    Domain-agnostic gate execution engine.
    
    Collects structured data through a series of gates, using LLM-assisted
    extraction and deterministic gate selection.
    """
    
    def __init__(self):
        self.mem = MemoryLogger("nexus.gate_engine")
        self.parser = GateJsonParser()
        self.prompt_builder = GatePromptBuilder()
        self.llm_service = GateLLMService()
        self.completion_checker = GateCompletionChecker()
        self.state_merger = GateStateMerger()
        self.gate_selector = GateSelector()
    
    async def execute_gate(
        self,
        user_text: str,
        gate_config: GateConfig,
        previous_state: Optional[GateState] = None,
        actor: Literal["user", "assistant"] = "user",
        session_id: Optional[int] = None,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> ConsultantResult:
        """
        Execute one gate turn: extract values from user input, merge state, select next gate.
        
        Args:
            user_text: User's input text
            gate_config: Configuration from prompt
            previous_state: Previous gate state (if any)
            actor: "user" (user input) or "assistant" (LLM-generated)
            session_id: Optional session ID for logging
            conversation_history: Optional list of previous messages [{"role": "user|assistant", "content": "..."}]
        
        Returns:
            ConsultantResult with decision, next question, and updated state
        """
        self.mem.log_thinking(
            f"[GATE_ENGINE] execute_gate | Actor: {actor} | "
            f"Previous gates: {len(previous_state.gates) if previous_state else 0}"
        )
        
        # DETERMINISTIC PATH: If no user input, determine next gate without LLM call
        if not user_text or not user_text.strip():
            self.mem.log_thinking("[GATE_ENGINE] No user input - using deterministic path")
            return self._deterministic_next_gate(
                gate_config=gate_config,
                previous_state=previous_state
            )
        
        # LLM PATH: Only when there's actual user input
        self.mem.log_thinking("[GATE_ENGINE] User input detected - using LLM extraction path")
        
        # Step 1: Build LLM prompt for extraction
        llm_prompt = self.prompt_builder.build_extraction_prompt(
            user_text=user_text,
            gate_config=gate_config,
            current_state=previous_state,
            conversation_history=conversation_history
        )
        
        # Step 2: Call LLM for extraction
        llm_response = await self.llm_service.extract_gate_values(
            prompt=llm_prompt,
            gate_config=gate_config,
            session_id=session_id,
            user_id=user_id
        )
        
        # Step 3: Parse LLM response
        parse_result = self.parser.parse(
            payload=llm_response,
            gate_config=gate_config,
            previous_state=previous_state,
            actor=actor
        )
        
        if not parse_result.ok:
            # Parsing failed - return error result
            self.mem.log_artifact(f"Parsing failed: {[e.message for e in parse_result.errors]}")
            return self._create_error_result(
                gate_config=gate_config,
                previous_state=previous_state,
                errors=parse_result.errors
            )
        
        # Step 4: Merge state (preserve previous, update only answered gates)
        merged_state = self.state_merger.merge(
            previous_state=previous_state,
            parsed_state=parse_result.canonical_state,
            gate_config=gate_config,
            user_text=user_text
        )
        
        # Step 5: Select next gate (hybrid: LLM recommendation + deterministic)
        next_gate_key = self.gate_selector.select_next(
            gate_config=gate_config,
            current_state=merged_state,
            llm_recommendation=parse_result.canonical_state.status.next_gate
        )
        
        # Step 6: Compute completion status
        completion_result = self.completion_checker.check(
            gate_config=gate_config,
            current_state=merged_state,
            user_override=self.completion_checker.detect_user_override(user_text)
        )
        
        # Step 7: Build final state with computed status
        final_state = GateState(
            summary=merged_state.summary,
            gates=merged_state.gates,
            status=StatusInfo(
                pass_=completion_result[0],  # Use system-computed decision
                next_gate=next_gate_key,
                next_query=self.gate_selector.get_question_for_gate(next_gate_key, gate_config) if next_gate_key else None
            )
        )
        
        # Step 8: Determine which gates were updated
        updated_gates = self._get_updated_gates(
            previous_state=previous_state,
            current_state=final_state,
            diff=parse_result.diff
        )
        
        # Step 9: Build result
        decision = self._map_decision(completion_result[1])
        
        return ConsultantResult(
            decision=decision,
            pass_=final_state.status.pass_,
            next_gate=final_state.status.next_gate,
            next_question=final_state.status.next_query,
            proposed_state=final_state,
            updated_gates=updated_gates
        )
    
    # Methods have been moved to services/engines:
    # - _build_extraction_prompt → GatePromptBuilder.build_extraction_prompt()
    # - _call_llm → GateLLMService.extract_gate_values()
    # - _merge_state → GateStateMerger.merge()
    # - _select_next_gate → GateSelector.select_next()
    # - _check_completion → GateCompletionChecker.check()
    # - _detect_user_override → GateCompletionChecker.detect_user_override()
    # - _get_question_for_gate → GateSelector.get_question_for_gate()
    
    def _deterministic_next_gate(
        self,
        gate_config: GateConfig,
        previous_state: Optional[GateState]
    ) -> ConsultantResult:
        """
        Deterministically determine next gate without LLM call.
        Used when there's no user input to process.
        """
        if not previous_state:
            # First gate - return first gate in order
            first_gate_key = gate_config.gate_order[0] if gate_config.gate_order else None
            if not first_gate_key:
                # No gates defined - return error
                return self._create_error_result(
                    gate_config=gate_config,
                    previous_state=None,
                    errors=[ParseError(message="No gates defined in gate_config", field="gate_order")]
                )
            
            first_gate_def = gate_config.gates.get(first_gate_key)
            first_question = first_gate_def.question if first_gate_def else "Let's get started"
            
            initial_state = GateState(
                summary="",
                gates={},
                status=StatusInfo(
                    pass_=False,
                    next_gate=first_gate_key,
                    next_query=first_question
                )
            )
            
            return ConsultantResult(
                decision=GateDecision.NEXT_GATE,
                pass_=False,
                next_question=first_question,
                proposed_state=initial_state,
                updated_gates=[],
                reasoning="Initial gate - no user input yet"
            )
        
        # Find first missing gate deterministically using GateSelector
        next_gate_key = self.gate_selector.select_next(
            gate_config=gate_config,
            current_state=previous_state,
            llm_recommendation=None
        )
        
        if next_gate_key:
            next_question = self.gate_selector.get_question_for_gate(next_gate_key, gate_config)
            return ConsultantResult(
                decision=GateDecision.NEXT_GATE,
                pass_=False,
                next_question=next_question,
                proposed_state=GateState(
                    summary=previous_state.summary,
                    gates=previous_state.gates,
                    status=StatusInfo(
                        pass_=False,
                        next_gate=next_gate_key,
                        next_query=next_question
                    )
                ),
                updated_gates=[],
                reasoning=f"Deterministic: next gate is {next_gate_key}"
            )
        
        # All gates complete (deterministic check)
        completion_result = self.completion_checker.check(
            gate_config=gate_config,
            current_state=previous_state,
            user_override=False
        )
        
        return ConsultantResult(
            decision=GateDecision.PASS if completion_result[0] else GateDecision.NEXT_GATE,
            pass_=completion_result[0],
            next_question=None,
            proposed_state=GateState(
                summary=previous_state.summary,
                gates=previous_state.gates,
                status=StatusInfo(
                    pass_=completion_result[0],
                    next_gate=None,
                    next_query=None
                )
            ),
            updated_gates=[],
            reasoning="Deterministic: all gates appear complete"
        )
    
    # Completion checking, user override detection, and question retrieval
    # have been moved to GateCompletionChecker and GateSelector
    
    def _get_updated_gates(
        self,
        previous_state: Optional[GateState],
        current_state: GateState,
        diff: Optional[Any]  # GateDiff from parser
    ) -> list[str]:
        """
        Determine which gates were updated this turn.
        """
        if not previous_state:
            # First turn - all gates in current state are new
            return list(current_state.gates.keys())
        
        updated = []
        for gate_key in current_state.gates:
            prev_value = previous_state.gates.get(gate_key)
            curr_value = current_state.gates[gate_key]
            
            if prev_value is None:
                # New gate
                updated.append(gate_key)
            else:
                # Check if value changed
                if prev_value.raw != curr_value.raw or prev_value.classified != curr_value.classified:
                    updated.append(gate_key)
        
        return updated
    
    def _map_decision(self, decision: GateDecision) -> GateDecision:
        """
        Map GateDecision enum to itself (for consistency).
        """
        return decision
    
    def _create_error_result(
        self,
        gate_config: GateConfig,
        previous_state: Optional[GateState],
        errors: list
    ) -> ConsultantResult:
        """
        Create error result when parsing fails.
        """
        # Find first missing required gate for next question
        next_gate_key = None
        next_question = None
        
        if previous_state:
            next_gate_key = self.gate_selector.select_next(
                gate_config=gate_config,
                current_state=previous_state,
                llm_recommendation=None
            )
            if next_gate_key:
                next_question = self.gate_selector.get_question_for_gate(next_gate_key, gate_config)
        
        # Use previous state or create empty state
        error_state = previous_state or GateState(
            summary="",
            gates={},
            status=StatusInfo(pass_=False, next_gate=next_gate_key, next_query=next_question)
        )
        
        return ConsultantResult(
            decision=GateDecision.FAIL_REQUIRED_MISSING,
            pass_=False,
            next_gate=next_gate_key,
            next_question=next_question,
            proposed_state=error_state,
            updated_gates=[]
        )

