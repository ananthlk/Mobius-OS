"""
Calendar Tool - Manages patient calendar events and appointments.
⚠️ WARNING: Only for scheduling non-clinical appointments with patient consent.
"""
from typing import Any, Dict, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime
import uuid

class PatientCalendarManager(NexusTool):
    """
    Manages calendar events and appointments for patients.
    ⚠️ WARNING: This tool may only be used to schedule non-clinical appointments 
    for patients who have provided explicit consent. Clinical appointment scheduling 
    must use approved clinical systems.
    """
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="patient_calendar_manager",
            description="Creates or updates calendar events for a patient. ⚠️ WARNING: Only for scheduling non-clinical appointments. Requires patient consent. Clinical appointments must use approved clinical systems.",
            parameters={
                "patient_id": "str (Patient identifier)",
                "event_type": "str (Event type: 'appointment', 'reminder', 'consultation', 'follow_up')",
                "start_time": "str (Event start time in ISO 8601 format: YYYY-MM-DDTHH:MM:SS)",
                "end_time": "str (Event end time in ISO 8601 format: YYYY-MM-DDTHH:MM:SS)",
                "title": "str (Event title/subject)",
                "location": "Optional[str] (Event location or address)",
                "reminder_minutes": "Optional[int] (Minutes before event to send reminder, default: 60)"
            }
        )
    
    def run(
        self, 
        patient_id: str, 
        event_type: str, 
        start_time: str, 
        end_time: str, 
        title: str, 
        location: Optional[str] = None,
        reminder_minutes: Optional[int] = 60
    ) -> Dict[str, Any]:
        """
        Creates or updates a calendar event for a patient.
        Mock implementation - in production, this would integrate with a calendar service.
        """
        # Validate event type
        valid_event_types = ["appointment", "reminder", "consultation", "follow_up"]
        if event_type not in valid_event_types:
            event_type = "appointment"
        
        # Parse dates (basic validation)
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        except Exception:
            duration_minutes = 0
        
        # Mock implementation
        return {
            "patient_id": patient_id,
            "event_id": f"CAL_{uuid.uuid4().hex[:8]}",
            "event_type": event_type,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": duration_minutes,
            "location": location,
            "reminder_minutes": reminder_minutes,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
            "warning": "This is a mock implementation. Ensure patient consent before scheduling. Clinical appointments require approved systems."
        }







