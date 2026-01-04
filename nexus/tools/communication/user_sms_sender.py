"""
User SMS Sender - Sends SMS from user's authenticated SMS account.
⚠️ WARNING: Only for non-clinical, pre-approved messages with patient consent.
SMS is unencrypted.
"""
import os
import logging
from typing import Any, Dict, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid

logger = logging.getLogger("nexus.tools.user_sms_sender")

API_BASE_URL = os.getenv("MOBIUS_API_URL", "http://localhost:8000")


class UserSMSSender(NexusTool):
    """
    Sends SMS from user's authenticated SMS account.
    """

    def __init__(self):
        super().__init__()
        self.api_base_url = API_BASE_URL

    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="user_sms_sender",
            description="Sends SMS from user's authenticated SMS account. User must have authorized SMS service access. Currently supports Twilio integration.",
            parameters={
                "to": "str (Recipient phone number in E.164 format, e.g., +1234567890)",
                "message": "str (SMS message content, max 160 characters recommended per segment)",
                "user_id": "Optional[str] (User ID for authentication - defaults to system user)",
                "sender_phone": "Optional[str] (Phone number to send from - uses user's configured number if not specified)"
            }
        )

    def run(
        self,
        to: str,
        message: str,
        user_id: Optional[str] = None,
        sender_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an SMS from a user's authenticated SMS account.
        Currently a stub implementation - will integrate with user's SMS service credentials.
        """
        # Get user_id (default to system user if not provided)
        if not user_id:
            user_id = "system"  # TODO: Get from context/session

        message_length = len(message)
        estimated_segments = (message_length // 160) + 1 if message_length > 160 else 1

        # TODO: Implement user SMS authentication/credential storage similar to Gmail OAuth
        # For now, this is a stub that would use user's SMS service credentials
        # In production, this would:
        # 1. Retrieve user's SMS service credentials (e.g., Twilio credentials stored per user)
        # 2. Use those credentials to send SMS
        # 3. Return real message ID and status

        logger.warning("User SMS sender is currently a stub implementation. Real SMS sending not yet implemented for user accounts.")

        return {
            "message_id": f"SMS_{uuid.uuid4().hex[:8]}",
            "from": sender_phone or "user_configured_number",
            "to": to,
            "message": message,
            "message_length": message_length,
            "estimated_segments": estimated_segments,
            "sent_at": datetime.now().isoformat(),
            "status": "sent",
            "method": "user_sms_service",
            "warning": "This is a stub implementation. Real SMS sending for user accounts not yet implemented."
        }

