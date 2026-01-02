"""
Email Tool - Sends pre-approved emails to patients.
⚠️ WARNING: Only for non-clinical, pre-approved messages with patient consent.
"""
from typing import Any, Dict, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid

class PatientEmailSender(NexusTool):
    """
    Sends emails to patients.
    ⚠️ WARNING: This tool may only be used to send pre-approved, non-clinical messages 
    to patients who have provided explicit consent. Clinical information must never be 
    transmitted through this channel.
    """
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="patient_email_sender",
            description="Sends email to a patient. ⚠️ WARNING: Only for pre-approved, non-clinical messages. Requires patient consent. Clinical information must never be transmitted through this channel.",
            parameters={
                "patient_id": "str (Patient identifier)",
                "subject": "str (Email subject line)",
                "body": "str (Email body content)",
                "template_id": "Optional[str] (Pre-approved template identifier)",
                "priority": "Optional[str] (Priority level: 'low', 'normal', 'high', default: 'normal')"
            }
        )
    
    def run(
        self, 
        patient_id: str, 
        subject: str, 
        body: str, 
        template_id: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Sends an email to a patient.
        Mock implementation - in production, this would integrate with an email service.
        """
        # Validate priority
        valid_priorities = ["low", "normal", "high"]
        if priority not in valid_priorities:
            priority = "normal"
        
        # Mock implementation
        return {
            "patient_id": patient_id,
            "message_id": f"EMAIL_{uuid.uuid4().hex[:8]}",
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "status": "sent",
            "template_id": template_id,
            "priority": priority,
            "channel": "email",
            "warning": "This is a mock implementation. Ensure patient consent and message approval before sending."
        }

