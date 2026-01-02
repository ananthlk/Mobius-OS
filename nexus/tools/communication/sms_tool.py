"""
SMS Tool - Sends pre-approved SMS messages to patients.
⚠️ WARNING: Only for non-clinical, pre-approved messages with patient consent.
SMS is unencrypted.
"""
from typing import Any, Dict, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid

class PatientSMSSender(NexusTool):
    """
    Sends SMS messages to patients.
    ⚠️ WARNING: This tool may only be used to send pre-approved, non-clinical messages 
    to patients who have provided explicit consent. SMS is unencrypted and clinical 
    information must never be transmitted through this channel.
    """
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="patient_sms_sender",
            description="Sends SMS to a patient. ⚠️ WARNING: Only for pre-approved, non-clinical messages. Requires patient consent. SMS is unencrypted. Clinical information must never be transmitted through this channel.",
            parameters={
                "patient_id": "str (Patient identifier)",
                "message": "str (SMS message content, max 160 characters recommended)",
                "template_id": "Optional[str] (Pre-approved template identifier)",
                "urgency": "Optional[str] (Urgency level: 'low', 'medium', 'high', default: 'medium')"
            }
        )
    
    def run(
        self, 
        patient_id: str, 
        message: str, 
        template_id: Optional[str] = None,
        urgency: str = "medium"
    ) -> Dict[str, Any]:
        """
        Sends an SMS to a patient.
        Mock implementation - in production, this would integrate with an SMS service.
        """
        # Validate urgency
        valid_urgency_levels = ["low", "medium", "high"]
        if urgency not in valid_urgency_levels:
            urgency = "medium"
        
        # Check message length (SMS typically 160 chars per message)
        message_length = len(message)
        estimated_segments = (message_length // 160) + 1 if message_length > 160 else 1
        
        # Mock implementation
        return {
            "patient_id": patient_id,
            "message_id": f"SMS_{uuid.uuid4().hex[:8]}",
            "message": message,
            "message_length": message_length,
            "estimated_segments": estimated_segments,
            "sent_at": datetime.now().isoformat(),
            "status": "sent",
            "template_id": template_id,
            "urgency": urgency,
            "channel": "sms",
            "warning": "This is a mock implementation. SMS is unencrypted. Ensure patient consent and message approval before sending."
        }

