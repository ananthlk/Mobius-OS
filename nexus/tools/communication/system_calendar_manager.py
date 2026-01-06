"""
System Calendar Manager - Manages calendar events from system account.
Uses Google Calendar API with service account or OAuth.
"""
from typing import Any, Dict, Optional, List
from nexus.core.base_tool import NexusTool, ToolSchema
from datetime import datetime, timedelta
import uuid
import os
import logging

logger = logging.getLogger("nexus.tools.system_calendar")

# System calendar configuration
SYSTEM_CALENDAR_EMAIL = os.getenv("SYSTEM_CALENDAR_EMAIL", "mobiushealthai@gmail.com")


class SystemCalendarManager(NexusTool):
    """
    Manages calendar events from the system account calendar.
    Can read and create events in the system calendar.
    """
    
    def __init__(self):
        super().__init__()
        # For system calendar, we can use OAuth with system account or service account
        # For now, using the same OAuth mechanism but with system credentials
        self.system_email = SYSTEM_CALENDAR_EMAIL
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="system_calendar_manager",
            description="Manages calendar events in the system calendar. Can read events and create new events. Uses system account (mobiushealthai@gmail.com).",
            parameters={
                "operation": "str (Operation: 'list_events', 'create_event', 'get_event')",
                "calendar_id": "Optional[str] (Calendar ID, default: 'primary')",
                "time_min": "Optional[str] (Start time for list_events, ISO 8601 format)",
                "time_max": "Optional[str] (End time for list_events, ISO 8601 format)",
                "max_results": "Optional[int] (Max results for list_events, default: 10)",
                "event_id": "Optional[str] (Event ID for get_event operation)",
                "event_summary": "Optional[str] (Event title for create_event)",
                "event_start": "Optional[str] (Event start time for create_event, ISO 8601 format)",
                "event_end": "Optional[str] (Event end time for create_event, ISO 8601 format)",
                "event_description": "Optional[str] (Event description for create_event)",
                "event_location": "Optional[str] (Event location for create_event)",
                "attendees": "Optional[List[str]] (List of attendee email addresses for create_event)"
            }
        )
    
    async def _get_calendar_service(self):
        """Get Calendar API service for system account."""
        # For system calendar, we could use:
        # 1. Service account credentials (if available)
        # 2. OAuth with system account credentials
        # 3. Or reuse the calendar_oauth_service with system user_id
        
        # For now, using OAuth service with system user_id
        from nexus.modules.calendar_oauth import calendar_oauth_service
        service = await calendar_oauth_service.get_calendar_service("system", self.system_email)
        return service
    
    async def run_async(
        self,
        operation: str,
        calendar_id: Optional[str] = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: Optional[int] = 10,
        event_id: Optional[str] = None,
        event_summary: Optional[str] = None,
        event_start: Optional[str] = None,
        event_end: Optional[str] = None,
        event_description: Optional[str] = None,
        event_location: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Performs calendar operations (list, create, get events).
        This is the async version.
        """
        try:
            service = await self._get_calendar_service()
            
            if not service:
                raise ValueError("Calendar service not available. System calendar OAuth credentials not configured.")
            
            if operation == "list_events":
                # List events
                time_min_param = time_min or (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
                time_max_param = time_max or (datetime.now() + timedelta(days=30)).isoformat() + 'Z'
                
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min_param,
                    timeMax=time_max_param,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                
                return {
                    "operation": "list_events",
                    "calendar_id": calendar_id,
                    "events_count": len(events),
                    "events": [
                        {
                            "id": event.get('id'),
                            "summary": event.get('summary'),
                            "start": event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                            "end": event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                            "description": event.get('description'),
                            "location": event.get('location'),
                            "attendees": [a.get('email') for a in event.get('attendees', [])]
                        }
                        for event in events
                    ],
                    "time_range": {
                        "start": time_min_param,
                        "end": time_max_param
                    }
                }
            
            elif operation == "create_event":
                # Create event
                if not event_summary or not event_start or not event_end:
                    raise ValueError("event_summary, event_start, and event_end are required for create_event")
                
                event_body = {
                    'summary': event_summary,
                    'description': event_description,
                    'location': event_location,
                    'start': {
                        'dateTime': event_start,
                        'timeZone': 'UTC',
                    },
                    'end': {
                        'dateTime': event_end,
                        'timeZone': 'UTC',
                    },
                }
                
                if attendees:
                    event_body['attendees'] = [{'email': email} for email in attendees]
                
                created_event = service.events().insert(
                    calendarId=calendar_id,
                    body=event_body
                ).execute()
                
                return {
                    "operation": "create_event",
                    "calendar_id": calendar_id,
                    "event_id": created_event.get('id'),
                    "summary": created_event.get('summary'),
                    "start": created_event.get('start', {}).get('dateTime'),
                    "end": created_event.get('end', {}).get('dateTime'),
                    "html_link": created_event.get('htmlLink'),
                    "status": "created"
                }
            
            elif operation == "get_event":
                # Get specific event
                if not event_id:
                    raise ValueError("event_id is required for get_event")
                
                event = service.events().get(
                    calendarId=calendar_id,
                    eventId=event_id
                ).execute()
                
                return {
                    "operation": "get_event",
                    "calendar_id": calendar_id,
                    "event_id": event.get('id'),
                    "summary": event.get('summary'),
                    "start": event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                    "end": event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                    "description": event.get('description'),
                    "location": event.get('location'),
                    "attendees": [a.get('email') for a in event.get('attendees', [])],
                    "html_link": event.get('htmlLink'),
                    "status": event.get('status')
                }
            
            else:
                raise ValueError(f"Unknown operation: {operation}. Supported: 'list_events', 'create_event', 'get_event'")
        
        except Exception as e:
            logger.error(f"Calendar operation failed: {e}")
            raise ValueError(f"Calendar operation failed: {str(e)}")
    
    def run(
        self,
        operation: str,
        calendar_id: Optional[str] = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: Optional[int] = 10,
        event_id: Optional[str] = None,
        event_summary: Optional[str] = None,
        event_start: Optional[str] = None,
        event_end: Optional[str] = None,
        event_description: Optional[str] = None,
        event_location: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Performs calendar operations (list, create, get events).
        Synchronous wrapper - calls async version.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.run_async(
                operation=operation,
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max,
                max_results=max_results,
                event_id=event_id,
                event_summary=event_summary,
                event_start=event_start,
                event_end=event_end,
                event_description=event_description,
                event_location=event_location,
                attendees=attendees
            )
        )



