import logging
import json
from typing import Dict, Any
from nexus.modules.config_manager import config_manager
from nexus.modules.llm_service import llm_service
from nexus.core.memory_logger import MemoryLogger

logger = logging.getLogger("nexus.diary_brain")

class DiaryBrain:
    """
    The Literary Agent for Development Diaries.
    Transforms raw development metrics into beautiful, reflective prose.
    """
    
    def __init__(self):
        self.mem = MemoryLogger("nexus.diary_brain")
    
    async def write_entry(self, data: Dict[str, Any]) -> str:
        """
        Generates a beautiful prose diary entry from development metrics.
        """
        self.mem.log_thinking(f"[DIARY_BRAIN] Writing entry for {data.get('today', 'today')}")
        
        # Check if database is available before trying to use LLM
        db_available = False
        try:
            from nexus.modules.database import database
            # Try a simple connection check
            if hasattr(database, '_connection') and database._connection:
                db_available = True
            else:
                # Try to connect
                try:
                    await database.connect()
                    db_available = True
                except:
                    pass
        except:
            pass
        
        # Get model context (only if DB is available)
        model_context = None
        if db_available:
            try:
                model_context = await config_manager.resolve_app_context("diary", "system")
            except Exception as e:
                logger.debug(f"Could not resolve model context: {e}")
                model_context = None
        
        # Use fallback if no model context
        if not model_context:
            logger.info("Using fallback prose (database/LLM not available)")
            return self._fallback_prose(data)
        
        # Build the prompt
        prompt = self._build_prompt(data)
        
        # System instruction for beautiful prose
        system_instruction = """You are a thoughtful engineering journal writer for Mobius OS, an AI-powered operating system for managing workflows and relationships.

Your task is to write a beautiful, reflective diary entry in prose form. The entry should:
- Be written in first person ("I", "we")
- Feel personal and authentic, like a developer reflecting on their work
- Highlight struggles, breakthroughs, and moments of clarity
- Connect technical changes to their human impact
- Use elegant, flowing prose - not bullet points or lists
- Be approximately 3-5 paragraphs
- Capture the emotional journey of development, not just facts

Write as if you are the system itself, reflecting on its own evolution. Be poetic but grounded in reality."""

        try:
            self.mem.log_thinking(f"Invoking LLM for diary prose (Model: {model_context.get('model_id', 'unknown')})")
            
            prose = await llm_service.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                model_context=model_context
            )
            
            # Check if we got an error message instead of prose
            if prose and not prose.startswith("Error:"):
                self.mem.log_artifact(f"Generated diary prose: {len(prose)} characters")
                return prose.strip()
            else:
                logger.debug(f"LLM returned error, using fallback")
                return self._fallback_prose(data)
            
        except Exception as e:
            logger.debug(f"LLM generation failed, using fallback: {str(e)[:100]}")
            # Fallback to simple prose
            return self._fallback_prose(data)
    
    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """Builds the context prompt from data."""
        lines = []
        lines.append(f"Today is {data.get('today', 'today')}. Last diary entry was {data.get('last_run', 'never')}.")
        lines.append("")
        
        # Add conversation/session context if available
        conversation_context = data.get('conversation_context', '')
        if conversation_context:
            lines.append("=== Our Development Session ===")
            lines.append("The following is a transcript of our conversation during this development session:")
            lines.append("")
            lines.append(conversation_context)
            lines.append("")
            lines.append("=== End of Session Transcript ===")
            lines.append("")
        
        lines.append("Development Activity:")
        lines.append(f"- Codebase: {data.get('python_lines', 0)} Python lines, {data.get('typescript_lines', 0)} TypeScript lines")
        
        commits = data.get('commits', [])
        if commits:
            lines.append(f"- {len(commits)} commits since last entry:")
            for commit in commits[:5]:  # Top 5
                lines.append(f"  • {commit.get('message', 'No message')} ({commit.get('time', 'unknown time')})")
        
        new_files = data.get('new_files', [])
        if new_files:
            lines.append(f"- {len(new_files)} new files created")
            for f in new_files[:5]:
                lines.append(f"  • {f}")
        
        deleted_files = data.get('deleted_files', [])
        if deleted_files:
            lines.append(f"- {len(deleted_files)} files deleted")
            for f in deleted_files[:3]:
                lines.append(f"  • {f}")
        
        modified_files = data.get('modified_files', [])
        if modified_files:
            lines.append(f"- {len(modified_files)} files modified")
        
        lines.append("")
        if conversation_context:
            lines.append("Write a beautiful, reflective diary entry about this development session. Focus on:")
            lines.append("- What we discussed and built together")
            lines.append("- The challenges we faced and how we solved them")
            lines.append("- Key decisions made and why")
            lines.append("- The emotional journey of our collaboration")
            lines.append("- What we learned and what's next")
        else:
            lines.append("Write a beautiful, reflective diary entry about this development session.")
        
        return "\n".join(lines)
    
    def _fallback_prose(self, data: Dict[str, Any]) -> str:
        """Fallback prose if LLM fails."""
        commits_count = len(data.get('commits', []))
        new_count = len(data.get('new_files', []))
        
        return f"""Today marked another step in the evolution of Mobius OS. The codebase continues to grow, with {data.get('python_lines', 0)} lines of Python and {data.get('typescript_lines', 0)} lines of TypeScript forming the foundation of our system.

Since the last entry, {'we made ' + str(commits_count) + ' commits' if commits_count > 0 else 'the system has been quiet'}. {'New modules emerged' if new_count > 0 else 'The existing architecture was refined'}, each change a small step toward a more capable system.

The work continues, each line of code a thread in the larger tapestry of what Mobius OS is becoming."""

# Singleton
diary_brain = DiaryBrain()

