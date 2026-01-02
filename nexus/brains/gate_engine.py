"""
Gate Engine - Domain-agnostic gate execution engine.

Replaces ConsultantBrain with a config-driven approach for collecting
structured workflow requirements through gates.
"""

import logging
import json
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
    GateDecisionResult
)
from nexus.modules.llm_service import llm_service
from nexus.modules.config_manager import config_manager
from nexus.core.memory_logger import MemoryLogger

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
        llm_prompt = self._build_extraction_prompt(
            user_text=user_text,
            gate_config=gate_config,
            current_state=previous_state,
            conversation_history=conversation_history
        )
        
        # Step 2: Call LLM for extraction
        llm_response = await self._call_llm(
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
        merged_state = self._merge_state(
            previous_state=previous_state,
            parsed_state=parse_result.canonical_state,
            gate_config=gate_config,
            user_text=user_text
        )
        
        # Step 5: Select next gate (hybrid: LLM recommendation + deterministic)
        next_gate_key = self._select_next_gate(
            gate_config=gate_config,
            current_state=merged_state,
            llm_recommendation=parse_result.canonical_state.status.next_gate
        )
        
        # Step 6: Compute completion status
        completion_result = self._check_completion(
            gate_config=gate_config,
            current_state=merged_state,
            user_override=self._detect_user_override(user_text)
        )
        
        # Step 7: Build final state with computed status
        final_state = GateState(
            summary=merged_state.summary,
            gates=merged_state.gates,
            status=StatusInfo(
                pass_=completion_result[0],  # Use system-computed decision
                next_gate=next_gate_key,
                next_query=self._get_question_for_gate(next_gate_key, gate_config) if next_gate_key else None
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
    
    def _build_extraction_prompt(
        self,
        user_text: str,
        gate_config: GateConfig,
        current_state: Optional[GateState],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Build prompt for LLM to extract gate values from user input.
        
        The prompt instructs the LLM to:
        1. Extract raw/classified values for each gate
        2. Recommend next gate (with confidence)
        3. Update summary if needed
        """
        parts = []
        
        # System instructions
        parts.append(gate_config.system_instructions)
        
        # LLM Role
        if gate_config.llm_role:
            parts.append("\n\nYour Role:")
            for role_item in gate_config.llm_role:
                parts.append(f"  - {role_item}")
        
        # Current state
        if current_state:
            parts.append("\n\nCurrent Gate State:")
            parts.append(f"Summary: {current_state.summary}")
            parts.append("\nGates:")
            for gate_key in gate_config.gate_order:
                gate_def = gate_config.gates.get(gate_key)
                if not gate_def:
                    continue
                
                gate_value = current_state.gates.get(gate_key)
                status = "✓" if gate_value and gate_value.classified else "✗"
                parts.append(f"  {status} {gate_key}: {gate_def.question}")
                if gate_value and gate_value.raw:
                    parts.append(f"    Current: {gate_value.raw}")
        else:
            parts.append("\n\nCurrent Gate State: (empty - starting fresh)")
        
        # Gate Definitions (CRITICAL - LLM needs to know valid gate keys)
        parts.append("\n\nAvailable Gates (you MUST use these exact gate keys):")
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                continue
            
            parts.append(f"\n  Gate Key: '{gate_key}'")
            parts.append(f"    Question: {gate_def.question}")
            parts.append(f"    Required: {gate_def.required}")
            if gate_def.expected_categories:
                parts.append(f"    Expected Categories: {', '.join(gate_def.expected_categories)}")
            else:
                parts.append(f"    Expected Categories: (any value - free text)")
        
        # Conversation history (NEW)
        if conversation_history:
            parts.append("\n\nConversation History:")
            parts.append("The following is the conversation so far:")
            # Show last 10 messages to avoid token bloat
            for msg in conversation_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Truncate very long messages
                if len(content) > 500:
                    content = content[:500] + "... [truncated]"
                parts.append(f"\n{role.capitalize()}: {content}")
            parts.append("\n--- End of Conversation History ---")
        
        # Current user input
        parts.append(f"\n\nCurrent User Input: {user_text}")
        
        # Instructions
        parts.append("\n\nYour Task:")
        parts.append("1. Extract gate values from the user input")
        parts.append("2. Update the 'gates' object with raw (verbatim) and classified (categorized) values")
        parts.append("3. SYNTHESIZE a comprehensive summary that integrates ALL gate values into a cohesive problem statement:")
        parts.append("   - Include patient info availability status (what data is available)")
        parts.append("   - Include use case/purpose (why this check is needed)")
        parts.append("   - Include ineligibility handling (what happens if check fails)")
        parts.append("   - Include urgency/timeline (how soon this is needed)")
        parts.append("   - Example: 'User has urgent need (Within 48 Hours) to determine eligibility for clinical programming. Has insurance info. If ineligible, must find state alternatives.'")
        parts.append("4. Set 'status.next_gate' to recommend the next gate to ask (or null if done)")
        parts.append("5. Set 'status.next_query' to the exact question to ask next")
        parts.append("6. Set 'status.pass' to true only if ALL required gates have classified values")
        
        # Output format
        parts.append("\n\nOutput Format (JSON only):")
        parts.append(json.dumps(gate_config.strict_json_schema, indent=2))
        
        # Pre-filled template to prevent hallucination
        parts.append("\n\nExample JSON Template (fill in values, keep structure):")
        template = {
            "summary": "",
            "gates": {},
            "status": {
                "pass": False,
                "next_gate": None,
                "next_query": None
            }
        }
        
        # Pre-fill gates structure with all gate keys
        for gate_key in gate_config.gate_order:
            template["gates"][gate_key] = {
                "raw": None,
                "classified": None,
                "confidence": None
            }
        
        parts.append(json.dumps(template, indent=2))
        parts.append("\n\nIMPORTANT: Use the exact gate keys listed above. Do not invent new keys.")
        
        # Summary synthesis requirement (CRITICAL)
        parts.append("\n\nCRITICAL: Summary Synthesis Requirement:")
        parts.append("The 'summary' field must be a COMPREHENSIVE SYNTHESIS of all gate values, not just a list.")
        parts.append("It should read as a cohesive problem statement that integrates:")
        parts.append("  - Patient information availability (from gate 1)")
        parts.append("  - Use case/purpose (from gate 2)")
        parts.append("  - Ineligibility handling/fallback (from gate 3)")
        parts.append("  - Urgency/timeline (from gate 4)")
        parts.append("Example: 'User has urgent need (Within 48 Hours) to determine Medicaid eligibility for clinical programming.")
        parts.append("Has patient demographics and insurance information. If ineligible, must explore state program alternatives.'")
        
        # Mandatory logic
        if gate_config.mandatory_logic:
            parts.append("\n\nMandatory Logic:")
            for logic in gate_config.mandatory_logic:
                parts.append(f"  - {logic}")
        
        return "\n".join(parts)
    
    async def _call_llm(
        self,
        prompt: str,
        gate_config: GateConfig,
        session_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Call LLM service to extract gate values.
        Emits enriched thinking messages before and after LLM call.
        """
        self.mem.log_thinking("[GATE_ENGINE] Calling LLM for extraction")
        
        # Resolve model context
        model_context = await config_manager.resolve_app_context(
            module_id="workflow",
            user_id=user_id or "system"  # Use provided user_id or fallback to system
        )
        
        # Build generation config from gate_config if available
        # For now, use defaults (can be enhanced later)
        generation_config = {
            "temperature": 0.3,  # Lower temperature for more deterministic extraction
            "max_output_tokens": 4096,
            "top_p": 0.95,
            "top_k": 40
        }
        
        # Build prompt key from gate_config
        # Uses new prompt key structure: workflow:eligibility:{strategy}:gate
        strategy = gate_config.path.get("strategy", "UNKNOWN") if isinstance(gate_config.path, dict) else "UNKNOWN"
        prompt_key = f"workflow:eligibility:{strategy}:gate"
        
        # Print prompt for debugging (enhanced visibility)
        print("\n" + "="*100)
        print("🔵 GATE ENGINE - LLM PROMPT")
        print("="*100)
        print(prompt)
        print("="*100 + "\n")
        
        # Emit enriched thinking BEFORE LLM call
        if session_id:
            try:
                from nexus.conductors.workflows.orchestrator import orchestrator
                await orchestrator.emit_llm_thinking(
                    session_id=session_id,
                    operation="GATE_ENGINE",
                    prompt=prompt,
                    system_instruction=None,  # Already in prompt
                    rag_citations=[],  # Gate engine doesn't use RAG yet
                    model_id=model_context.get("model_id"),
                    prompt_key=prompt_key
                )
            except Exception as e:
                self.mem.log_artifact(f"Failed to emit thinking before LLM call: {e}")
        
        # Call LLM with metadata
        response, metadata = await llm_service.generate_text(
            prompt=prompt,
            system_instruction=None,  # Already in prompt
            model_context=model_context,
            generation_config=generation_config,
            return_metadata=True  # Get metadata for after-call emission
        )
        
        # Emit enriched thinking AFTER LLM call
        if session_id:
            try:
                from nexus.conductors.workflows.orchestrator import orchestrator
                await orchestrator.emit_llm_thinking(
                    session_id=session_id,
                    operation="GATE_ENGINE",
                    prompt=prompt,
                    system_instruction=None,
                    rag_citations=[],
                    model_id=model_context.get("model_id"),
                    response_metadata=metadata,
                    prompt_key=prompt_key
                )
            except Exception as e:
                self.mem.log_artifact(f"Failed to emit thinking after LLM call: {e}")
        
        # Print response for debugging (enhanced visibility)
        print("\n" + "="*100)
        print("🟢 GATE ENGINE - LLM RESPONSE")
        print("="*100)
        print(response)
        print("="*100 + "\n")
        
        return response
    
    def _merge_state(
        self,
        previous_state: Optional[GateState],
        parsed_state: GateState,
        gate_config: GateConfig,
        user_text: str
    ) -> GateState:
        """
        Merge parsed state with previous state.
        
        Rules:
        - Start from previous_state if present
        - Only update gates that were explicitly answered
        - Preserve all existing values unless explicitly changed
        """
        # Start with previous state (preserve all existing values)
        if previous_state:
            merged = GateState(
                summary=previous_state.summary,
                gates={gate_key: GateValue(
                    raw=gate_value.raw,
                    classified=gate_value.classified,
                    confidence=gate_value.confidence,
                    collected_at=gate_value.collected_at
                ) for gate_key, gate_value in previous_state.gates.items()},
                status=previous_state.status
            )
        else:
            merged = GateState(
                summary="",
                gates={},
                status=StatusInfo(pass_=False, next_gate=None, next_query=None)
            )
        
        # Update summary if parsed state has a new one
        if parsed_state.summary and parsed_state.summary.strip():
            merged.summary = parsed_state.summary.strip()[:2000]  # Enforce 2000 char limit
        
        # Update gates that were explicitly answered (have raw values in parsed_state)
        for gate_key in gate_config.gate_order:
            parsed_gate_value = parsed_state.gates.get(gate_key)
            if not parsed_gate_value:
                continue
            
            # Only update if raw value is present (user explicitly answered)
            if parsed_gate_value.raw:
                merged.gates[gate_key] = GateValue(
                    raw=parsed_gate_value.raw,
                    classified=parsed_gate_value.classified,
                    confidence=parsed_gate_value.confidence,
                    collected_at=datetime.now()
                )
            # Also handle explicit clearing (raw is None but gate exists in parsed_state)
            elif gate_key in parsed_state.gates and parsed_gate_value.raw is None:
                # Check if user explicitly cleared (would need more sophisticated detection)
                # For now, only update if classified is also None (clear signal)
                if parsed_gate_value.classified is None:
                    # User cleared - remove gate value
                    if gate_key in merged.gates:
                        del merged.gates[gate_key]
        
        return merged
    
    def _select_next_gate(
        self,
        gate_config: GateConfig,
        current_state: GateState,
        llm_recommendation: Optional[str] = None
    ) -> Optional[str]:
        """
        Hybrid gate selection: LLM recommendation + deterministic gate_order.
        
        Per MANDATORY_LOGIC:
        - If LLM confidence = 100% (indicated by recommendation) → use LLM recommendation
        - Otherwise → use deterministic gate_order to find first missing required gate
        - Always respect gate_order sequence
        """
        # Helper to check if gate is missing
        def is_gate_missing(gate_key: str) -> bool:
            gate_value = current_state.gates.get(gate_key)
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                return False
            # Gate is missing if required and classified is None
            if gate_def.required:
                return gate_value is None or gate_value.classified is None
            # For optional gates, missing if no value at all
            return gate_value is None
        
        # 1. Check LLM recommendation (if provided and valid)
        if llm_recommendation:
            if llm_recommendation in gate_config.gate_order:
                gate_def = gate_config.gates.get(llm_recommendation)
                if gate_def and is_gate_missing(llm_recommendation):
                    # LLM recommended a valid missing gate - use it
                    return llm_recommendation
        
        # 2. Deterministic: find FIRST missing REQUIRED gate in gate_order
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                continue
            if gate_def.required and is_gate_missing(gate_key):
                return gate_key
        
        # 3. If no required gates missing, check optional gates
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                continue
            if not gate_def.required and is_gate_missing(gate_key):
                return gate_key
        
        # All gates complete
        return None
    
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
        
        # Find first missing required gate deterministically
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                continue
            
            if gate_def.required:
                gate_value = previous_state.gates.get(gate_key)
                if not gate_value or not gate_value.classified:
                    # Found missing required gate
                    return ConsultantResult(
                        decision=GateDecision.NEXT_GATE,
                        pass_=False,
                        next_question=gate_def.question,
                        proposed_state=GateState(
                            summary=previous_state.summary,
                            gates=previous_state.gates,
                            status=StatusInfo(
                                pass_=False,
                                next_gate=gate_key,
                                next_query=gate_def.question
                            )
                        ),
                        updated_gates=[],
                        reasoning=f"Deterministic: next required gate is {gate_key}"
                    )
        
        # Check optional gates
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def or gate_def.required:
                continue
            
            gate_value = previous_state.gates.get(gate_key)
            if not gate_value or not gate_value.classified:
                # Found missing optional gate
                return ConsultantResult(
                    decision=GateDecision.NEXT_GATE,
                    pass_=False,
                    next_question=gate_def.question,
                    proposed_state=GateState(
                        summary=previous_state.summary,
                        gates=previous_state.gates,
                        status=StatusInfo(
                            pass_=False,
                            next_gate=gate_key,
                            next_query=gate_def.question
                        )
                    ),
                    updated_gates=[],
                    reasoning=f"Deterministic: next optional gate is {gate_key}"
                )
        
        # All gates complete (deterministic check)
        completion_result = self._check_completion(
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
    
    def _check_completion(
        self,
        gate_config: GateConfig,
        current_state: GateState,
        user_override: bool = False
    ) -> Tuple[bool, GateDecision]:
        """
        Check completion status using hierarchy:
        1. User override (highest)
        2. All required gates met
        3. Fail (some required gates missing)
        
        Per MANDATORY_LOGIC step 7: "If no required gates are missing, set status.pass=true"
        """
        if user_override:
            return (True, GateDecision.PASS_OVERRIDE)
        
        # Check required gates
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def or not gate_def.required:
                continue
            
            gate_value = current_state.gates.get(gate_key)
            # Gate is missing if classified is None
            if gate_value is None or gate_value.classified is None:
                return (False, GateDecision.FAIL_REQUIRED_MISSING)
        
        # All required gates have classified values
        return (True, GateDecision.PASS_REQUIRED_GATES)
    
    def _detect_user_override(self, user_text: str) -> bool:
        """
        Detect if user explicitly overrides (says "skip", "move on", etc.).
        """
        override_phrases = [
            "skip", "move on", "next", "continue", "proceed",
            "that's fine", "good enough", "let's go"
        ]
        user_lower = user_text.lower()
        return any(phrase in user_lower for phrase in override_phrases)
    
    def _get_question_for_gate(
        self,
        gate_key: Optional[str],
        gate_config: GateConfig
    ) -> Optional[str]:
        """
        Get the question text for a gate key.
        """
        if not gate_key:
            return None
        gate_def = gate_config.gates.get(gate_key)
        if not gate_def:
            return None
        return gate_def.question.strip()
    
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
            for gate_key in gate_config.gate_order:
                gate_def = gate_config.gates.get(gate_key)
                if not gate_def or not gate_def.required:
                    continue
                gate_value = previous_state.gates.get(gate_key)
                if gate_value is None or gate_value.classified is None:
                    next_gate_key = gate_key
                    next_question = gate_def.question
                    break
        
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

