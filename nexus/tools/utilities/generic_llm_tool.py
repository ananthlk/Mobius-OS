"""
Generic LLM Call Tool - Makes generic LLM API calls using the LLM Gateway.
"""
from typing import Any, Dict, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
import asyncio

class GenericLLMCallTool(NexusTool):
    """
    Makes a generic LLM API call using the configured LLM gateway.
    This tool leverages the existing LLM Gateway infrastructure for governance and routing.
    """
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="generic_llm_call",
            description="Makes a generic LLM API call using the configured LLM gateway. Supports custom prompts, model selection, and temperature control.",
            parameters={
                "prompt": "str (The prompt/message to send to the LLM)",
                "model_id": "Optional[str] (Specific model to use, defaults to configured model)",
                "temperature": "Optional[float] (Sampling temperature, 0.0-2.0, default: 0.7)",
                "max_tokens": "Optional[int] (Maximum tokens in response, default: 1000)"
            }
        )
    
    def run(
        self, 
        prompt: str, 
        model_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1000
    ) -> Dict[str, Any]:
        """
        Makes a generic LLM API call.
        Note: The LLM Gateway is async, but this tool interface is sync.
        In production, this would need async handling or an async wrapper.
        """
        # Validate temperature
        if temperature < 0.0 or temperature > 2.0:
            temperature = 0.7
        
        # Validate max_tokens
        if max_tokens and max_tokens < 1:
            max_tokens = 1000
        
        # Mock implementation - in production, this would call:
        # from nexus.modules.llm_gateway import gateway
        # response = await gateway.chat_completion(
        #     messages=[{"role": "user", "content": prompt}],
        #     model_id=model_id,
        #     module_id="generic_llm_tool",
        #     user_id="system"
        # )
        # return response
        
        return {
            "prompt": prompt,
            "model_id": model_id or "default_model",
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response": f"Mock LLM response to: {prompt[:100]}...",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 50,
                "total_tokens": len(prompt.split()) + 50
            },
            "note": "This is a mock implementation. In production, integrate with nexus.modules.llm_gateway.gateway.chat_completion() (async method)."
        }







