"""
System Email Sender - Sends emails from system account (mobiushealthai@gmail.com) via SMTP.
"""
from typing import Any, Dict, Optional, List
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("nexus.tools.system_email")

# System email configuration
SYSTEM_EMAIL = os.getenv("SYSTEM_EMAIL", "mobiushealthai@gmail.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


class SystemEmailSender(NexusTool):
    """
    Sends emails from the system account (mobiushealthai@gmail.com) via SMTP.
    """
    
    def __init__(self):
        super().__init__()
        self.email_password = os.getenv("EMAIL_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD")
        self.system_email = SYSTEM_EMAIL
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        
        if not self.email_password:
            logger.warning("System email password not configured (EMAIL_PASSWORD or EMAIL_APP_PASSWORD). Email sending will fail.")
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="system_email_sender",
            description="Sends email from system account (mobiushealthai@gmail.com) via SMTP. Requires EMAIL_PASSWORD environment variable.",
            parameters={
                "to": "str (Recipient email address)",
                "subject": "str (Email subject line)",
                "message": "str (Email body content)",
                "cc": "Optional[List[str]] (CC recipients - list of email addresses)",
                "attachments": "Optional[List[Dict]] (Attachments - list of {'filename': str, 'content': bytes, 'content_type': str})"
            }
        )
    
    def run(
        self,
        to: str,
        subject: str,
        message: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Sends an email from the system account via SMTP.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message: Email body content
            cc: Optional list of CC recipient emails
            attachments: Optional list of attachment dicts with 'filename', 'content' (bytes), and 'content_type'
        
        Returns:
            Dict with send status and message details
        """
        if not self.email_password:
            raise ValueError("System email password not configured (EMAIL_PASSWORD or EMAIL_APP_PASSWORD). Cannot send email.")
        
        message_id = f"EMAIL_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.system_email
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
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.system_email, self.email_password)
                
                # Combine to and cc recipients
                recipients = [to]
                if cc:
                    recipients.extend(cc)
                
                server.send_message(msg, to_addrs=recipients)
            
            logger.info(f"Email sent from system account to {to}, message_id: {message_id}")
            
            return {
                "message_id": message_id,
                "from": self.system_email,
                "to": to,
                "cc": cc or [],
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
                "status": "sent",
                "method": "smtp",
                "attachments_count": len(attachments) if attachments else 0
            }
        except Exception as e:
            logger.error(f"Failed to send email from system account: {e}")
            raise ValueError(f"Failed to send email: {str(e)}")




