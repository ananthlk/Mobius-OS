"""
System SMS Sender - Sends SMS from system account via SMS service provider (e.g., Twilio).
⚠️ WARNING: Only for non-clinical, pre-approved messages with patient consent.
SMS is unencrypted.
"""
import os
import logging
from typing import Any, Dict, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid

logger = logging.getLogger("nexus.tools.system_sms_sender")

# SMS Configuration - Twilio example
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")  # System phone number


class SystemSMSSender(NexusTool):
    """
    Sends SMS from system account via SMS service provider (e.g., Twilio).
    """

    def __init__(self):
        super().__init__()
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.phone_number = TWILIO_PHONE_NUMBER

        if not self.account_sid or not self.auth_token or not self.phone_number:
            logger.warning("SMS credentials not configured (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER). SMS sending will fail.")

    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="system_sms_sender",
            description="Sends SMS from system account via SMS service provider (e.g., Twilio). Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables.",
            parameters={
                "to": "str (Recipient phone number in E.164 format, e.g., +1234567890)",
                "message": "str (SMS message content, max 160 characters recommended per segment)",
            }
        )

    def run(
        self,
        to: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Sends an SMS from the system account via SMS service provider.
        """
        if not self.account_sid or not self.auth_token or not self.phone_number:
            raise ValueError("SMS credentials not configured (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER). Cannot send SMS from system account.")

        message_length = len(message)
        estimated_segments = (message_length // 160) + 1 if message_length > 160 else 1

        try:
            # Try to use Twilio if available
            try:
                from twilio.rest import Client

                client = Client(self.account_sid, self.auth_token)

                message_response = client.messages.create(
                    body=message,
                    from_=self.phone_number,
                    to=to
                )

                logger.info(f"SMS sent successfully from system account to {to}, message_sid: {message_response.sid}")

                return {
                    "message_id": message_response.sid,
                    "from": self.phone_number,
                    "to": to,
                    "message": message,
                    "message_length": message_length,
                    "estimated_segments": estimated_segments,
                    "sent_at": datetime.now().isoformat(),
                    "status": message_response.status,
                    "method": "twilio",
                    "price": message_response.price,
                    "price_unit": message_response.price_unit
                }
            except ImportError:
                raise ValueError("Twilio library not installed. Install with: pip install twilio")
            except Exception as e:
                logger.error(f"Failed to send SMS via Twilio: {e}")
                raise ValueError(f"Failed to send SMS: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to send SMS from system account: {e}")
            raise ValueError(f"Failed to send SMS: {str(e)}")






