"""
Gate LLM Service

Handles LLM calls for gate extraction.
Extracted from GateEngine to isolate LLM integration concerns.
"""

import logging
from typing import Optional

from nexus.core.gate_models import GateConfig
from nexus.modules.llm_service import llm_service
from nexus.modules.config_manager import config_manager

logger = logging.getLogger("nexus.services.gate.llm_service")


class GateLLMService:
    """Handles LLM calls for gate extraction."""
    
    async def extract_gate_values(
        self,
        prompt: str,
        gate_config: GateConfig,
        session_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Call LLM service to extract gate values.
        
        Emits enriched thinking messages before and after LLM call.
        
        Args:
            prompt: The complete prompt for LLM
            gate_config: The gate configuration
            session_id: Optional session ID for logging
            user_id: Optional user ID for model resolution
            
        Returns:
            LLM response string
        """
        logger.debug("Calling LLM for gate extraction")
        
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
                logger.warning(f"Failed to emit thinking before LLM call: {e}")
        
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
                logger.warning(f"Failed to emit thinking after LLM call: {e}")
        
        # Print response for debugging (enhanced visibility)
        print("\n" + "="*100)
        print("🟢 GATE ENGINE - LLM RESPONSE")
        print("="*100)
        print(response)
        print("="*100 + "\n")
        
        return response




