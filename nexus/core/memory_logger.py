import logging
from typing import Any

class MemoryLogger:
    """
    Standardized logger for the Mobius 4-Layer Memory Architecture.
    Inherit from this or compose it to ensure consistent audit traces.
    """
    def __init__(self, logger_name: str):
        self._logger = logging.getLogger(logger_name)

    def log_thinking(self, message: str):
        """Layer 2: Transparent Thinking (Transient Logic)"""
        self._logger.info(f"🧠 [MEMORY:THINKING] {message}")

    def log_persistence(self, message: str):
        """Layer 1: Long-term Storage (DB Writes)"""
        self._logger.debug(f"💾 [MEMORY:PERSISTENCE] {message}")

    def log_artifact(self, message: str):
        """Layer 3: artifacts (Retrieval/drafts)"""
        self._logger.info(f"🗂️  [MEMORY:ARTIFACTS] {message}")

    def log_output(self, message: str):
        """Layer 4: User Output (Surface)"""
        self._logger.info(f"📨 [MEMORY:OUTPUT] {message}")

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
