"""
Eligibility Agent V2 - Router

FastAPI endpoints for the Eligibility Agent V2.
"""
import logging
import re
import json
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from nexus.agents.eligibility_v2.orchestrator import EligibilityOrchestrator
from nexus.agents.eligibility_v2.models import UIEvent
from nexus.brains.conversational_agent import conversational_agent
from nexus.services.shaping.session_repository import ShapingSessionRepository

logger = logging.getLogger("nexus.eligibility_v2.router")

router = APIRouter(prefix="/api/eligibility-v2", tags=["eligibility_v2"])
orchestrator = EligibilityOrchestrator()
session_repo = ShapingSessionRepository()


class SessionStartRequest(BaseModel):
    """Request model for starting a session"""
    user_id: str


async def _load_conversation_history(session_id: int) -> list:
    """Load conversation history from session transcript"""
    try:
        session = await session_repo.get_transcript(session_id)
        if session and session.get("transcript"):
            return session["transcript"]
        return []
    except Exception as e:
        logger.warning(f"Failed to load conversation history: {e}")
        return []


async def _emit_process_event(session_id: Optional[int], phase: str, status: str, message: str, data: Optional[dict] = None):
    """Helper to emit process events"""
    if session_id:
        await orchestrator._emit_process_event(session_id, phase, status, message, data)


@router.post("/session/start")
async def start_session(request: SessionStartRequest):
    """Create a new eligibility session"""
    try:
        session_id = await session_repo.create_simple(request.user_id)
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/{case_id}/turn")
async def submit_user_message(
    case_id: str,
    ui_event: UIEvent,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID")
):
    """Process a user message turn"""
    session_id = int(x_session_id) if x_session_id else None
    user_id = x_user_id or "system"
    
    # Extract patient_id from message if not in header
    patient_id = x_patient_id
    if not patient_id and ui_event.event_type == "user_message":
        message_text = ui_event.data.get("message", "")
        # Look for MRN pattern
        mrn_match = re.search(r'MRN\s*(\w+)', message_text, re.IGNORECASE)
        if mrn_match:
            patient_id = f"MRN{mrn_match.group(1)}"
        elif re.search(r'(?:for|patient)\s+MRN\s*(\w+)', message_text, re.IGNORECASE):
            mrn_match = re.search(r'(?:for|patient)\s+MRN\s*(\w+)', message_text, re.IGNORECASE)
            patient_id = f"MRN{mrn_match.group(1)}"
    
    # Store user message in OUTPUT bucket for process event filtering
    if session_id and ui_event.event_type == "user_message":
        try:
            from nexus.modules.database import database
            import json
            await database.execute(
                query="""
                INSERT INTO memory_events (session_id, bucket_type, payload)
                VALUES (:sid, 'OUTPUT', :payload)
                """,
                values={
                    "sid": session_id,
                    "payload": json.dumps({
                        "role": "user",
                        "content": ui_event.data.get("message", ""),
                        "timestamp": ui_event.timestamp
                    })
                }
            )
            logger.debug(f"Stored user message in OUTPUT bucket for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to store user message: {e}")
    
    # Process turn
    result = await orchestrator.process_turn(
        case_id=case_id,
        ui_event=ui_event,
        session_id=session_id,
        patient_id=patient_id
    )
    
    # Format presentation_summary through conversational agent
    raw_summary = result.get("presentation_summary", "")
    if not raw_summary or not raw_summary.strip():
        # If no summary was generated, create a fallback response
        logger.warning(f"No presentation_summary generated for case {case_id}, creating fallback")
        score_state = result.get("score_state", {})
        base_probability = score_state.get("base_probability", 0) if isinstance(score_state, dict) else getattr(score_state, "base_probability", 0)
        raw_summary = f"Thank you for providing that information. Based on the eligibility check, the payment probability is {base_probability:.1%}. I'm processing your eligibility assessment."
        result["presentation_summary"] = raw_summary
    
    if raw_summary:
        await _emit_process_event(session_id, "conversation", "in_progress", "Conversation engine initiated - formatting response...")
        
        try:
            conversation_history = await _load_conversation_history(session_id)
            
            # Extract visit-specific probability data from case_state
            visit_probabilities = []
            case_state = result.get("case_state")
            if case_state:
                if hasattr(case_state, 'timing'):
                    timing = case_state.timing
                elif isinstance(case_state, dict):
                    timing = case_state.get("timing", {})
                else:
                    timing = {}
                
                related_visits = timing.get("related_visits", []) if isinstance(timing, dict) else getattr(timing, "related_visits", [])
                
                if related_visits:
                    for visit in related_visits:
                        if isinstance(visit, dict):
                            visit_date = visit.get("visit_date")
                            probability = visit.get("eligibility_probability")
                            status = visit.get("eligibility_status")
                            event_tense = visit.get("event_tense")
                            visit_type = visit.get("visit_type")
                        else:
                            visit_date = visit.visit_date.isoformat() if visit.visit_date else None
                            probability = visit.eligibility_probability
                            status = visit.eligibility_status.value if visit.eligibility_status else None
                            event_tense = visit.event_tense.value if visit.event_tense else None
                            visit_type = visit.visit_type
                        
                        if visit_date and probability is not None:
                            visit_probabilities.append({
                                "visit_date": visit_date if isinstance(visit_date, str) else visit_date.isoformat() if visit_date else None,
                                "eligibility_probability": float(probability) if probability is not None else None,
                                "eligibility_status": status if isinstance(status, str) else status.value if status else None,
                                "event_tense": event_tense if isinstance(event_tense, str) else event_tense.value if event_tense else None,
                                "visit_type": visit_type
                            })
            
            formatted_summary = await conversational_agent.format_response(
                raw_response=raw_summary,
                user_id=user_id,
                context={
                    "session_id": session_id,
                    "conversation_history": conversation_history,
                    "operation": "eligibility_response",
                    "source": "eligibility_v2",
                    "visit_probabilities": visit_probabilities  # Pass visit-specific data
                }
            )
            result["presentation_summary"] = formatted_summary
            logger.debug(f"Formatted presentation_summary through conversational agent (length: {len(formatted_summary)})")
            
            await _emit_process_event(
                session_id,
                "conversation",
                "complete",
                "Conversation complete",
                {"conversation_summary": formatted_summary[:200] + "..." if len(formatted_summary) > 200 else formatted_summary}
            )
        except Exception as e:
            logger.warning(f"Failed to format presentation_summary through conversational agent: {e}", exc_info=True)
            await _emit_process_event(session_id, "conversation", "error", f"Conversation formatting error: {str(e)}")
            # Ensure we still have a response even if formatting fails
            if not result.get("presentation_summary"):
                result["presentation_summary"] = raw_summary
    
    # Format next_questions through conversational agent
    next_questions = result.get("next_questions", [])
    if next_questions:
        try:
            conversation_history = await _load_conversation_history(session_id)
            
            formatted_questions = []
            for question in next_questions:
                if isinstance(question, dict):
                    question_text = question.get("text", "")
                    if question_text:
                        try:
                            formatted_text = await conversational_agent.format_response(
                                raw_response=question_text,
                                user_id=user_id,
                                context={
                                    "session_id": session_id,
                                    "conversation_history": conversation_history,
                                    "operation": "eligibility_question",
                                    "source": "eligibility_v2"
                                }
                            )
                            question["text"] = formatted_text
                            formatted_questions.append(question)
                        except Exception as e:
                            logger.warning(f"Failed to format question: {e}")
                            formatted_questions.append(question)
                else:
                    formatted_questions.append(question)
            
            result["next_questions"] = formatted_questions
            logger.debug(f"Formatted {len(formatted_questions)} questions through conversational agent")
        except Exception as e:
            logger.warning(f"Failed to format next_questions: {e}")
    
    # Store formatted response in OUTPUT bucket for SSE streaming
    if session_id:
        try:
            from nexus.modules.database import database
            import json
            from datetime import datetime, timezone
            output_payload = {
                "role": "assistant",
                "content": result.get("presentation_summary", ""),
                "presentation_summary": result.get("presentation_summary", ""),
                "next_questions": result.get("next_questions", []),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await database.execute(
                query="""
                INSERT INTO memory_events (session_id, bucket_type, payload)
                VALUES (:sid, 'OUTPUT', :payload)
                """,
                values={
                    "sid": session_id,
                    "payload": json.dumps(output_payload)
                }
            )
            logger.debug(f"Stored assistant response in OUTPUT bucket for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to store assistant response: {e}")
    
    return result


@router.get("/cases/{case_id}/view")
async def get_case_view(
    case_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """Get current case view"""
    try:
        from nexus.services.eligibility_v2.case_repository import CaseRepository
        from nexus.services.eligibility_v2.scoring_repository import ScoringRepository
        from nexus.services.eligibility_v2.turn_repository import TurnRepository
        
        case_repo = CaseRepository()
        scoring_repo = ScoringRepository()
        turn_repo = TurnRepository()
        
        case_pk = await case_repo.get_or_create_case(case_id, int(x_session_id) if x_session_id else None)
        case_record = await case_repo.get_case(case_pk)
        
        case_state = await case_repo.get_case_state(case_pk)
        latest_score = await scoring_repo.get_latest_score(case_pk)
        latest_plan = await turn_repo.get_latest_plan(case_pk)
        
        return {
            "case_id": case_id,
            "case_pk": case_pk,
            "session_id": case_record.session_id if case_record else None,
            "status": case_record.status if case_record else "INIT",
            "case_state": case_state.model_dump() if case_state else {},
            "score_state": latest_score.model_dump() if latest_score else None,
            "next_questions": latest_plan.get("next_questions", []) if latest_plan else [],
            "improvement_plan": latest_plan.get("improvement_plan", []) if latest_plan else [],
            "presentation_summary": latest_plan.get("presentation_summary", "") if latest_plan else ""
        }
    except Exception as e:
        logger.error(f"Failed to get case view: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}/process-events")
async def get_process_events(
    case_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """Get all process events for the session (persists across turns)"""
    session_id = int(x_session_id) if x_session_id else None
    if not session_id:
        return {"events": []}
    
    try:
        from nexus.modules.database import database
        
        # Get ALL process events for this session (not filtered by turn)
        # This ensures thinking messages from previous turns remain visible
        query = """
            SELECT payload, created_at, bucket_type
            FROM memory_events 
            WHERE session_id = :sid 
            AND (bucket_type = 'ELIGIBILITY_PROCESS' OR bucket_type = 'THINKING')
            ORDER BY created_at ASC
        """
        results = await database.fetch_all(
            query=query,
            values={"sid": session_id}
        )
        
        events = []
        thinking_messages_by_phase = {}  # Group thinking messages by phase
        process_events_by_phase = {}  # Track all process events by phase
        
        # First pass: collect thinking messages and process events separately
        for row in results:
            payload = row["payload"]
            bucket_type = row["bucket_type"]
            
            if isinstance(payload, str):
                payload = json.loads(payload)
            
            phase = payload.get("phase")
            
            # Skip thinking messages without a phase (they shouldn't exist but handle gracefully)
            if bucket_type == "THINKING":
                if not phase:
                    continue  # Skip thinking messages without a phase
                # Store thinking messages grouped by phase
                if phase not in thinking_messages_by_phase:
                    thinking_messages_by_phase[phase] = []
                parsed_metadata = _parse_metadata(payload.get("metadata"))
                logger.debug(f"📦 Thinking message for phase {phase}: message={payload.get('message')[:50]}, metadata.data_type={parsed_metadata.get('data_type') if parsed_metadata and isinstance(parsed_metadata, dict) else 'N/A'}")
                thinking_messages_by_phase[phase].append({
                    "message": payload.get("message"),
                    "metadata": parsed_metadata,
                    "timestamp": payload.get("timestamp") or row["created_at"].isoformat()
                })
            else:
                # Process event - skip if no phase
                if not phase:
                    continue
                    
                event = {
                    "phase": phase,
                    "status": payload.get("status"),
                    "message": payload.get("message"),
                    "timestamp": payload.get("timestamp") or row["created_at"].isoformat(),
                    "data": payload.get("data")
                }
                
                # Store all process events by phase (we'll attach thinking messages to the latest one)
                if phase not in process_events_by_phase:
                    process_events_by_phase[phase] = []
                process_events_by_phase[phase].append(event)
        
        # Second pass: attach thinking messages to the latest process event of each phase
        for phase, phase_events in process_events_by_phase.items():
            # Sort by timestamp to get the latest event
            phase_events.sort(key=lambda e: e["timestamp"])
            latest_event = phase_events[-1]
            
            # Attach thinking messages to the latest event
            if phase in thinking_messages_by_phase:
                latest_event["thinking_messages"] = thinking_messages_by_phase[phase]
                logger.debug(f"🔗 Attached {len(thinking_messages_by_phase[phase])} thinking messages to latest {phase} event")
            
            events.extend(phase_events)
        
        # Valid phases for placeholder events
        valid_phases = ["patient_loading", "interpretation", "scoring", "planning", "eligibility_check", "conversation"]
        
        # Track which phases have process events
        phases_with_process_events = set(process_events_by_phase.keys())
        
        # Add any remaining thinking messages that don't have a corresponding process event
        for phase, messages in thinking_messages_by_phase.items():
            if phase not in phases_with_process_events and phase in valid_phases:
                events.append({
                    "phase": phase,
                    "status": "in_progress",
                    "message": f"Loading {phase.replace('_', ' ')}...",
                    "timestamp": messages[0]["timestamp"] if messages else datetime.now().isoformat(),
                    "thinking_messages": messages
                })
        
        return {"events": events}
    except Exception as e:
        logger.error(f"Failed to get process events: {e}", exc_info=True)
        return {"events": []}


def _parse_metadata(metadata):
    """Parse metadata if it's a JSON string"""
    if metadata is None:
        return None
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            return metadata
    return metadata
