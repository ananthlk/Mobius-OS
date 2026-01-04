"""
User Email Sender - Sends emails from user's Gmail account via Gmail API with OAuth2.
"""
from typing import Any, Dict, Optional, List
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid
import os
import logging
import base64
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("nexus.tools.user_email")

# API Configuration
API_BASE_URL = os.getenv("MOBIUS_API_URL", "http://localhost:8000")


class UserEmailSender(NexusTool):
    """
    Sends emails from user's Gmail account via Gmail API with OAuth2.
    """
    
    def __init__(self):
        super().__init__()
        self.api_base_url = API_BASE_URL
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="user_email_sender",
            description="Sends email from user's Gmail account via Gmail API with OAuth2. User must have authorized Gmail access.",
            parameters={
                "to": "str (Recipient email address)",
                "subject": "str (Email subject line)",
                "message": "str (Email body content)",
                "cc": "Optional[List[str]] (CC recipients - list of email addresses)",
                "attachments": "Optional[List[Dict]] (Attachments - list of {'filename': str, 'content': bytes, 'content_type': str})",
                "user_id": "Optional[str] (User ID for OAuth - defaults to system user)",
                "sender_email": "Optional[str] (Gmail account to send from - uses first connected account if not specified)"
            }
        )
    
    async def _send_via_gmail_api(
        self,
        user_id: str,
        sender_email: Optional[str],
        to: str,
        subject: str,
        message: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email via Gmail API using OAuth2."""
        try:
            from nexus.modules.gmail_oauth import gmail_oauth_service
            
            # Get Gmail service for user
            service = await gmail_oauth_service.get_gmail_service(user_id, sender_email)
            
            if not service:
                raise ValueError(f"No Gmail OAuth credentials found for user {user_id}. Please authorize Gmail access first via /api/gmail/oauth/authorize")
            
            # Create message
            msg = MIMEMultipart()
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            # Add body
            msg.attach(MIMEText(message, 'plain'))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content = attachment.get('content')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    
                    if content:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}'
                        )
                        msg.attach(part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            message_id = send_message.get('id')
            
            logger.info(f"Email sent via Gmail API from user {user_id} to {to}, message_id: {message_id}")
            
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
        to: str,
        subject: str,
        message: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        sender_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email from user's Gmail account via Gmail API with OAuth2.
        This is the async version - use this in async contexts.
        """
        message_id = f"EMAIL_{uuid.uuid4().hex[:8]}"
        
        # Get user_id (default to system user if not provided)
        if not user_id:
            user_id = "system"  # TODO: Get from context/session
        
        try:
            # Send via Gmail API
            gmail_result = await self._send_via_gmail_api(
                user_id=user_id,
                sender_email=sender_email,
                to=to,
                subject=subject,
                message=message,
                cc=cc,
                attachments=attachments
            )
            
            return {
                "message_id": gmail_result.get("message_id", message_id),
                "to": to,
                "cc": cc or [],
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
                "status": "sent",
                "method": "gmail_api",
                "sender_email": sender_email or "first_connected_account",
                "attachments_count": len(attachments) if attachments else 0
            }
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            raise ValueError(f"Failed to send email: {str(e)}")
    
    def run(
        self,
        to: str,
        subject: str,
        message: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        sender_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email from user's Gmail account via Gmail API with OAuth2.
        Synchronous wrapper - calls async version.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.run_async(
                to=to,
                subject=subject,
                message=message,
                cc=cc,
                attachments=attachments,
                user_id=user_id,
                sender_email=sender_email
            )
        )

