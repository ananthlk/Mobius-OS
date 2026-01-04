"""
Email Tool - Sends pre-approved emails to patients using Gmail API with OAuth2.
⚠️ WARNING: Only for non-clinical, pre-approved messages with patient consent.
"""
from typing import Any, Dict, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid
import os
import logging
import base64
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("nexus.tools.email")

# API Configuration
API_BASE_URL = os.getenv("MOBIUS_API_URL", "http://localhost:8000")


class PatientEmailSender(NexusTool):
    """
    Sends emails to patients using Gmail API with OAuth2.
    ⚠️ WARNING: This tool may only be used to send pre-approved, non-clinical messages 
    to patients who have provided explicit consent. Clinical information must never be 
    transmitted through this channel.
    """
    
    def __init__(self):
        super().__init__()
        self.api_base_url = API_BASE_URL
    
    def _get_patient_email(self, patient_id: str) -> Optional[str]:
        """Get patient email from user profile API."""
        try:
            import httpx
            url = f"{self.api_base_url}/api/user-profiles/{patient_id}/system"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    system_data = response.json()
                    demographics = system_data.get("demographics", {})
                    return demographics.get("email")
        except Exception as e:
            logger.debug(f"Failed to fetch patient email from API: {e}")
        return None
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="email_sender",
            description="Sends email using Gmail API with OAuth2. Can send to any email address. When patient_id is provided, fetches patient email from system. ⚠️ WARNING: For patient communications, only send pre-approved, non-clinical messages with patient consent.",
            parameters={
                "recipient_email": "Optional[str] (Recipient email address - required if patient_id not provided)",
                "patient_id": "Optional[str] (Patient identifier - if provided, fetches email from patient profile)",
                "subject": "str (Email subject line)",
                "body": "str (Email body content)",
                "template_id": "Optional[str] (Pre-approved template identifier)",
                "priority": "Optional[str] (Priority level: 'low', 'normal', 'high', default: 'normal')",
                "user_id": "Optional[str] (User ID for OAuth - defaults to system user)",
                "sender_email": "Optional[str] (Gmail account to send from - uses first connected account if not specified)"
            }
        )
    
    async def _send_via_gmail_api(
        self,
        user_id: str,
        sender_email: Optional[str],
        to_email: str,
        subject: str,
        body: str,
        patient_id: str
    ) -> Dict[str, Any]:
        """Send email via Gmail API using OAuth2."""
        try:
            from nexus.modules.gmail_oauth import gmail_oauth_service
            
            # Get Gmail service for user
            service = await gmail_oauth_service.get_gmail_service(user_id, sender_email)
            
            if not service:
                raise ValueError(f"No Gmail OAuth credentials found for user {user_id}. Please authorize Gmail access first via /api/gmail/oauth/authorize")
            
            # Create message
            message = MIMEMultipart()
            message['To'] = to_email
            message['Subject'] = subject
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            message_id = send_message.get('id')
            
            logger.info(f"Email sent via Gmail API to {to_email} for patient {patient_id}, message_id: {message_id}")
            
            return {
                "success": True,
                "status": "sent",
                "gmail_api_used": True,
                "message_id": message_id
            }
        except Exception as e:
            logger.error(f"Failed to send email via Gmail API: {e}")
            raise
    
    async def run_async(
        self, 
        subject: str, 
        body: str, 
        recipient_email: Optional[str] = None,
        patient_id: Optional[str] = None,
        template_id: Optional[str] = None,
        priority: str = "normal",
        user_id: Optional[str] = None,
        sender_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email using Gmail API with OAuth2.
        Can send to any email address. If patient_id is provided, fetches email from patient profile.
        This is the async version - use this in async contexts.
        """
        # Validate priority
        valid_priorities = ["low", "normal", "high"]
        if priority not in valid_priorities:
            priority = "normal"
        
        message_id = f"EMAIL_{uuid.uuid4().hex[:8]}"
        
        # Get user_id (default to system user if not provided)
        if not user_id:
            user_id = "system"  # TODO: Get from context/session
        
        try:
            # Determine recipient email
            final_recipient_email = None
            
            if recipient_email:
                # Direct email address provided
                final_recipient_email = recipient_email
            elif patient_id:
                # Look up patient email from API
                final_recipient_email = self._get_patient_email(patient_id)
                if not final_recipient_email:
                    raise ValueError(f"Patient email not found for patient {patient_id}. Patient not found or API unavailable.")
            else:
                raise ValueError("Either recipient_email or patient_id must be provided")
            
            # Send via Gmail API
            gmail_result = await self._send_via_gmail_api(
                user_id=user_id,
                sender_email=sender_email,
                to_email=final_recipient_email,
                subject=subject,
                body=body,
                patient_id=patient_id or "N/A"
            )
            
            result = {
                "message_id": gmail_result.get("message_id", message_id),
                "subject": subject,
                "recipient": final_recipient_email,
                "sent_at": datetime.now().isoformat(),
                "status": "sent",
                "template_id": template_id,
                "priority": priority,
                "channel": "email",
                "gmail_api_used": True,
                "sender_email": sender_email or "first_connected_account"
            }
            
            if patient_id:
                result["patient_id"] = patient_id
            
            return result
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            raise ValueError(f"Failed to send email: {str(e)}")
    
    def run(
        self, 
        subject: str, 
        body: str, 
        recipient_email: Optional[str] = None,
        patient_id: Optional[str] = None,
        template_id: Optional[str] = None,
        priority: str = "normal",
        user_id: Optional[str] = None,
        sender_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email using Gmail API with OAuth2.
        Can send to any email address. If patient_id is provided, fetches email from patient profile.
        Synchronous wrapper - calls async version.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.run_async(
                subject=subject,
                body=body,
                recipient_email=recipient_email,
                patient_id=patient_id,
                template_id=template_id,
                priority=priority,
                user_id=user_id,
                sender_email=sender_email
            )
        )
