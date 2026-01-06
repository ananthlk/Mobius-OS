"""
Gate Prompt Builder

Builds prompts for gate extraction.
Extracted from GateEngine to separate prompt engineering concerns.
"""

import json
import logging
from typing import Optional, List, Dict

from nexus.core.gate_models import GateConfig, GateState

logger = logging.getLogger("nexus.services.gate.prompt_builder")


class GatePromptBuilder:
    """Builds prompts for gate extraction."""
    
    def build_extraction_prompt(
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
        
        Args:
            user_text: The user's input text
            gate_config: The gate configuration
            current_state: Optional current gate state
            conversation_history: Optional conversation history
            
        Returns:
            Complete prompt string for LLM
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
        
        # Conversation history
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
        
        # Explicit instruction for multi-gate extraction
        parts.append("\n\n⚠️ CRITICAL INSTRUCTION:")
        parts.append("The user may provide information for MULTIPLE gates in a single message.")
        parts.append("You MUST extract ALL gate values that can be determined from this input.")
        parts.append("Do NOT limit extraction to just one gate - scan the entire message for:")
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if gate_def:
                parts.append(f"  - {gate_key}: {gate_def.question}")
        parts.append("")
        parts.append("Example: If user says 'I have name, DOB, and insurance info, no history of problems, need for clinical, escalate if ineligible, need within 72 hours'")
        parts.append("→ Extract ALL gates: 1_patient_info_availability=Yes, 2_insurance_history=No, 3_use_case=Clinical, 4_ineligibility_handling=Escalate, 5_urgency_timeline=Within 48 Hours")
        parts.append("")
        
        # Instructions
        parts.append("\n\nYour Task:")
        parts.append("CRITICAL: Extract ALL gate values that can be determined from the user input.")
        parts.append("Do NOT limit yourself to a single gate - if the user provides information for multiple gates, extract ALL of them.")
        parts.append("")
        parts.append("1. Extract gate values from the user input:")
        parts.append("   - Scan the ENTIRE user input for information related to ANY gate")
        parts.append("   - Extract raw (verbatim) and classified (categorized) values for EACH gate that has information")
        parts.append("   - If user mentions multiple gates in one message, extract ALL of them")
        parts.append("   - Example: If user says 'I have name, DOB, and insurance info, no history of problems, need for clinical, escalate if ineligible, need within 72 hours'")
        parts.append("     → Extract: gate 1 (Yes), gate 2 (No), gate 3 (Clinical), gate 4 (Escalate), gate 5 (Within 48 Hours)")
        parts.append("2. Update the 'gates' object with raw (verbatim) and classified (categorized) values for ALL extracted gates")
        parts.append("3. SYNTHESIZE a comprehensive summary that integrates ALL gate values into a cohesive problem statement:")
        parts.append("   - Include patient info availability status (what data is available)")
        parts.append("   - Include insurance history consistency (if mentioned)")
        parts.append("   - Include use case/purpose (why this check is needed)")
        parts.append("   - Include ineligibility handling (what happens if check fails)")
        parts.append("   - Include urgency/timeline (how soon this is needed)")
        parts.append("   - Example: 'User has urgent need (Within 48 Hours) to determine eligibility for clinical programming. Has insurance info. If ineligible, must find state alternatives.'")
        parts.append("4. Set 'status.next_gate' to recommend the next gate to ask (or null if all gates are complete)")
        parts.append("5. Set 'status.next_query' to the exact question to ask next (or null if all gates are complete)")
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


