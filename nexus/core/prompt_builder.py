from typing import List, Dict, Optional, Any
import json

class PromptBuilder:
    """
    Dynamic Prompt Engine.
    Assembles complex prompts from modular components:
    - Persona/Role
    - Context (RAG, History)
    - Task Analysis
    - User/Org Constraints
    """
    
    def __init__(self):
        self._role = "You are a helpful AI assistant."
        self._context_items: List[str] = []
        self._task_description = ""
        self._constraints: List[str] = []
        self._output_format = ""
        self._examples: List[Dict] = []
        
    def set_role(self, role_description: str) -> 'PromptBuilder':
        """Sets the System Persona."""
        self._role = role_description
        return self

    def add_context(self, source: str, content: str) -> 'PromptBuilder':
        """Adds a labeled context item (e.g. 'Provider Manual', 'User History')."""
        self._context_items.append(f"--- {source} ---\n{content}")
        return self

    def add_rag_hits(self, hits: List[str]) -> 'PromptBuilder':
        """Helper to add multiple RAG snippets."""
        if hits:
            combined = "\n\n".join(hits)
            self.add_context("RELEVANT KNOWLEDGE (RAG)", combined)
        return self

    def set_task(self, task: str) -> 'PromptBuilder':
        """Sets the specific instruction/analysis request."""
        self._task_description = task
        return self

    def add_constraint(self, constraint: str) -> 'PromptBuilder':
        """Adds a behavioral constraint (e.g. 'Do not hallucinate')."""
        self._constraints.append(constraint)
        return self
    
    def set_output_format(self, format_instruction: str) -> 'PromptBuilder':
        """Defines the expected output structure."""
        self._output_format = format_instruction
        return self

    def build(self) -> str:
        """
        Compiles the components into a single coherent System Prompt.
        """
        parts = []
        
        # 1. Role (The Anchor)
        parts.append(f"### ROLE\n{self._role}")
        
        # 2. Context (The Data)
        if self._context_items:
            parts.append("### CONTEXT_DATA")
            parts.append("\n\n".join(self._context_items))
            
        # 3. Constraints (The Guardrails)
        if self._constraints:
            parts.append("### CONSTRAINTS")
            for c in self._constraints:
                parts.append(f"- {c}")
                
        # 4. Output Format
        if self._output_format:
            parts.append(f"### OUTPUT_FORMAT\n{self._output_format}")
            
        # 5. The Task (The Trigger)
        if self._task_description:
            parts.append(f"### CURRENT_TASK\n{self._task_description}")
            
        return "\n\n".join(parts)

    def build_as_messages(self, user_query: str) -> List[Dict[str, str]]:
        """
        Returns a list of messages compatible with standard Chat APIs.
        [ {role: system, content: ...}, {role: user, content: ...} ]
        """
        system_prompt = self.build()
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    
    def build_from_config(self, config: Dict[str, Any], context: Dict[str, Any] = None) -> 'PromptBuilder':
        """
        Build prompt from config dictionary (from prompt_templates).
        
        Args:
            config: Prompt config dict with ROLE, CONTEXT, ANALYSIS, etc.
            context: Optional context dict with rag_data, transcript, user_query
        """
        # Set role (ROLE, not LM_ROLE)
        if "ROLE" in config:
            self.set_role(config["ROLE"])
        
        # Add context
        if "CONTEXT" in config:
            self.add_context("CONTEXT", config["CONTEXT"])
        
        # Add MOBIUSOS_CONTEXT if available
        if "MOBIUSOS_CONTEXT" in config:
            mobius_context = config["MOBIUSOS_CONTEXT"]
            if isinstance(mobius_context, dict):
                context_str = f"System: {mobius_context.get('system_description', '')}\n"
                context_str += f"Domain: {mobius_context.get('primary_domain', '')}\n"
                if mobius_context.get("core_capabilities"):
                    context_str += f"Capabilities: {', '.join(mobius_context['core_capabilities'])}\n"
                self.add_context("MOBIUSOS_CONTEXT", context_str)
        
        # Add strategy context
        if "STRATEGY_CONTEXT" in config:
            strategy_ctx = config["STRATEGY_CONTEXT"]
            if isinstance(strategy_ctx, dict):
                self.add_context("STRATEGY_CONTEXT", json.dumps(strategy_ctx, indent=2))
        
        # Add RAG info
        if "RAG_INFO" in config and context:
            rag_info = config["RAG_INFO"]
            rag_data = context.get("rag_data", [])
            if rag_info.get("available") and rag_data:
                self.add_context("RAG_INFO", json.dumps(rag_data, indent=2))
            elif not rag_info.get("available") and rag_info.get("when_not_available"):
                # Include instruction about asking for documents
                self.add_context("RAG_INFO", rag_info.get("when_not_available", {}).get("action", ""))
        
        # Add conversation history
        if "CONVERSATION_HISTORY" in config and context:
            transcript = context.get("transcript", [])
            history_config = config["CONVERSATION_HISTORY"]
            last_n = history_config.get("use_last_n", 5)
            if transcript:
                recent = transcript[-last_n:] if len(transcript) > last_n else transcript
                self.add_context("CONVERSATION_HISTORY", json.dumps(recent, indent=2))
        
        # Add user preferences (if available in context)
        if "USER_PREFERENCES" in config:
            self.add_context("USER_PREFERENCES", config["USER_PREFERENCES"].get("instruction", ""))
        
        # Add user role (if available in context)
        if context and "user_role" in context:
            user_role = context.get("user_role")
            self.add_context("USER_ROLE", f"The user has role: {user_role}. Adjust your responses accordingly.")
        
        # Add organization context (if available in context)
        if "ORGANIZATION_CONTEXT" in config:
            self.add_context("ORGANIZATION_CONTEXT", config["ORGANIZATION_CONTEXT"].get("instruction", ""))
        
        # Add constraints
        if "CONSTRAINTS" in config:
            for constraint in config["CONSTRAINTS"]:
                self.add_constraint(constraint)
        
        # Set output format
        if "OUTPUT" in config:
            output_config = config["OUTPUT"]
            if isinstance(output_config, dict):
                if "schema" in output_config:
                    # Build format from schema
                    schema = output_config["schema"]
                    format_str = schema.get("description", "")
                    if "example" in schema:
                        format_str += "\n\nExample JSON structure:\n" + json.dumps(schema["example"], indent=2)
                    self.set_output_format(format_str)
                else:
                    self.set_output_format(output_config.get("format", ""))
            else:
                self.set_output_format(output_config)
        
        # Set task/analysis
        if "ANALYSIS" in config:
            self.set_task(config["ANALYSIS"])
        
        # Add stage guidance if available
        if "STAGE_GUIDANCE" in config and context:
            # Could add current stage detection logic here
            pass
        
        return self