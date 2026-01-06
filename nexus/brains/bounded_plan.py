"""
Bounded Plan Brain

Implements the blocker-driven progression system that converts DraftPlan → BoundPlanSpec.
This is the core of the planning phase that handles iterative blocker resolution.
"""
import logging
import json
import re
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field, asdict
from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager
from nexus.modules.config_manager import config_manager
from nexus.modules.llm_service import llm_service
from nexus.core.prompt_builder import PromptBuilder
from nexus.core.base_agent import BaseAgent

logger = logging.getLogger("nexus.bounded_plan")
logger.setLevel(logging.DEBUG)


@dataclass
class SessionState:
    """State management for bounded plan session."""
    session_id: int
    known_fields: Set[str] = field(default_factory=set)
    known_context: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Optional[Dict[str, Any]] = None
    granted_permissions: Set[str] = field(default_factory=set)
    timeline: Optional[Dict[str, Any]] = None
    escalation: Optional[Dict[str, Any]] = None
    last_bound_plan_spec: Optional[Dict[str, Any]] = None
    last_next_input_request: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "known_fields": list(self.known_fields),
            "known_context": self.known_context,
            "user_preferences": self.user_preferences,
            "granted_permissions": list(self.granted_permissions),
            "timeline": self.timeline,
            "escalation": self.escalation,
            "last_bound_plan_spec": self.last_bound_plan_spec,
            "last_next_input_request": self.last_next_input_request
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create from dictionary."""
        return cls(
            session_id=data.get("session_id", 0),
            known_fields=set(data.get("known_fields", [])),
            known_context=data.get("known_context", {}),
            user_preferences=data.get("user_preferences"),
            granted_permissions=set(data.get("granted_permissions", [])),
            timeline=data.get("timeline"),
            escalation=data.get("escalation"),
            last_bound_plan_spec=data.get("last_bound_plan_spec"),
            last_next_input_request=data.get("last_next_input_request")
        )


@dataclass
class DevelopOutput:
    """Output from develop_bound_plan() method."""
    bound_plan_spec: Dict[str, Any]
    plan_readiness: str  # "READY_FOR_COMPILATION" | "NEEDS_INPUT" | "BLOCKED"
    next_input_request: Optional[Dict[str, Any]] = None


@dataclass
class ControllerOutput:
    """Output from handle_user_message() method."""
    message: str
    question: Optional[str] = None
    plan_readiness: str = "NEEDS_INPUT"
    bound_plan_spec: Optional[Dict[str, Any]] = None


class BoundedPlanBrain:
    """
    Main controller for bounded plan generation.
    Handles iterative blocker resolution until plan is ready for compilation.
    """
    
    def __init__(self):
        logger.debug(f"[BoundedPlanBrain.__init__] ENTRY")
        logger.debug(f"[BoundedPlanBrain.__init__] EXIT | BoundedPlanBrain initialized")
    
    async def start_session(
        self,
        session_id: int,
        draft_plan: Dict[str, Any],
        task_master_catalogue: Dict[str, Any],
        tool_registry: List[Any],
        initial_known_fields: Optional[Set[str]] = None
    ) -> SessionState:
        """
        Start a new bounded plan session.
        
        Args:
            session_id: Session identifier
            draft_plan: Draft plan from shaping_sessions.draft_plan
            task_master_catalogue: Task catalog data
            tool_registry: List of available tools
            initial_known_fields: Optional initial known fields
        
        Returns:
            Initial SessionState
        """
        logger.debug(f"[BoundedPlanBrain.start_session] ENTRY | session_id={session_id}, draft_plan_keys={list(draft_plan.keys())}, tools_count={len(tool_registry)}")
        
        try:
            # Create initial session state
            session_state = SessionState(
                session_id=session_id,
                known_fields=initial_known_fields or set(),
                known_context={
                    "draft_plan_summary": {
                        "gates_count": len(draft_plan.get("gates", [])),
                        "total_steps": sum(len(gate.get("steps", [])) for gate in draft_plan.get("gates", []))
                    }
                }
            )
            
            logger.debug(f"[BoundedPlanBrain.start_session] STATE_CREATED | known_fields={len(session_state.known_fields)}, context_keys={list(session_state.known_context.keys())}")
            
            # Call develop_bound_plan to get initial state
            logger.debug(f"[BoundedPlanBrain.start_session] CALLING_develop_bound_plan | initial_call")
            develop_output = await self.develop_bound_plan(
                session_state=session_state,
                draft_plan=draft_plan,
                task_master_catalogue=task_master_catalogue,
                tool_registry=tool_registry
            )
            
            # Update session state with initial bound plan spec
            session_state.last_bound_plan_spec = develop_output.bound_plan_spec
            session_state.last_next_input_request = develop_output.next_input_request
            
            logger.debug(f"[BoundedPlanBrain.start_session] STATE_UPDATE | plan_readiness={develop_output.plan_readiness}, blockers={len(develop_output.bound_plan_spec.get('blockers', []))}")
            
            # Persist initial state
            await self._persist_session_state(session_id, session_state)
            logger.debug(f"[BoundedPlanBrain.start_session] STATE_PERSISTED | session_id={session_id}")
            
            logger.debug(f"[BoundedPlanBrain.start_session] EXIT | plan_readiness={develop_output.plan_readiness}")
            return session_state
            
        except Exception as e:
            logger.error(f"[BoundedPlanBrain.start_session] ERROR | error={str(e)}", exc_info=True)
            raise
    
    async def handle_user_message(
        self,
        session_state: SessionState,
        user_message: str,
        user_id: str,
        draft_plan: Dict[str, Any],
        task_master_catalogue: Dict[str, Any],
        tool_registry: List[Any]
    ) -> ControllerOutput:
        """
        Handle user message in the bounded plan flow.
        
        Args:
            session_state: Current session state
            user_message: User's message
            user_id: User identifier
            draft_plan: Draft plan
            task_master_catalogue: Task catalog
            tool_registry: Available tools
        
        Returns:
            ControllerOutput with message and question
        """
        logger.debug(f"[BoundedPlanBrain.handle_user_message] ENTRY | session_id={session_state.session_id}, message_length={len(user_message)}, known_fields={len(session_state.known_fields)}")
        
        try:
            # 1. Extract user input from message
            logger.debug(f"[BoundedPlanBrain.handle_user_message] EXTRACTING_INPUT | checking_last_input_request")
            extracted_fields = {}
            if session_state.last_next_input_request:
                writes_to = session_state.last_next_input_request.get("writes_to", [])
                logger.debug(f"[BoundedPlanBrain.handle_user_message] EXTRACTING_INPUT | writes_to={writes_to}")
                
                # Simple extraction: look for field names in user message
                for field_name in writes_to:
                    # Try to extract value (simple pattern matching)
                    # In production, this could use NLP or structured extraction
                    if field_name.lower() in user_message.lower():
                        # Extract value after field name
                        pattern = rf"{field_name}[:=]\s*([^\n,]+)"
                        match = re.search(pattern, user_message, re.IGNORECASE)
                        if match:
                            extracted_fields[field_name] = match.group(1).strip()
                            logger.debug(f"[BoundedPlanBrain.handle_user_message] FIELD_EXTRACTED | field={field_name}, value={extracted_fields[field_name]}")
                        else:
                            # If field name mentioned, assume entire message is the value
                            extracted_fields[field_name] = user_message.strip()
                            logger.debug(f"[BoundedPlanBrain.handle_user_message] FIELD_EXTRACTED | field={field_name}, value_from_message")
            
            # Update known_fields with extracted values
            if extracted_fields:
                old_fields_count = len(session_state.known_fields)
                session_state.known_fields.update(extracted_fields.keys())
                session_state.known_context.update(extracted_fields)
                logger.debug(f"[BoundedPlanBrain.handle_user_message] STATE_UPDATE | known_fields={old_fields_count} -> {len(session_state.known_fields)}, new_fields={list(extracted_fields.keys())}")
            
            # 2. Automatic Data Enrichment: Check if user name/info was provided
            logger.debug(f"[BoundedPlanBrain.handle_user_message] CHECKING_DATA_ENRICHMENT | checking_for_patient_info")
            patient_info_provided = False
            patient_identifier = None
            
            # Check if any extracted field suggests patient info
            patient_field_names = ["patient_name", "patient_id", "name", "user_name", "member_id"]
            for field_name in patient_field_names:
                if field_name in extracted_fields or field_name in session_state.known_fields:
                    patient_info_provided = True
                    patient_identifier = extracted_fields.get(field_name) or session_state.known_context.get(field_name) or user_message
                    logger.debug(f"[BoundedPlanBrain.handle_user_message] PATIENT_INFO_DETECTED | field={field_name}, identifier={patient_identifier}")
                    break
            
            # Also check if user message contains patient-like info
            if not patient_info_provided:
                # Simple heuristic: if message is short and looks like a name
                if len(user_message.split()) <= 3 and user_message.strip():
                    patient_info_provided = True
                    patient_identifier = user_message.strip()
                    logger.debug(f"[BoundedPlanBrain.handle_user_message] PATIENT_INFO_DETECTED | from_message_heuristic, identifier={patient_identifier}")
            
            if patient_info_provided and patient_identifier:
                logger.debug(f"[BoundedPlanBrain.handle_user_message] FETCHING_PATIENT_PROFILE | identifier={patient_identifier}")
                try:
                    patient_profile = await self._fetch_patient_profile(patient_identifier)
                    if patient_profile:
                        # Populate known_fields with patient data
                        old_fields_count = len(session_state.known_fields)
                        for key, value in patient_profile.items():
                            if value:  # Only add non-empty values
                                session_state.known_fields.add(key)
                                session_state.known_context[key] = value
                        logger.debug(f"[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_LOADED | fields_added={len(session_state.known_fields) - old_fields_count}, total_fields={len(session_state.known_fields)}")
                        
                        # Update known_context with patient summary
                        session_state.known_context["patient_profile_summary"] = {
                            "patient_id": patient_profile.get("patient_id"),
                            "has_emr_data": bool(patient_profile.get("emr_data")),
                            "has_system_data": bool(patient_profile.get("system_data")),
                            "has_health_plan_data": bool(patient_profile.get("health_plan_data"))
                        }
                        logger.debug(f"[BoundedPlanBrain.handle_user_message] PATIENT_SUMMARY_UPDATED | summary_keys={list(session_state.known_context.get('patient_profile_summary', {}).keys())}")
                    else:
                        logger.debug(f"[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_NOT_FOUND | identifier={patient_identifier}")
                except Exception as e:
                    logger.warning(f"[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_FETCH_FAILED | error={str(e)}", exc_info=True)
            
            # 3. Call develop_bound_plan
            logger.debug(f"[BoundedPlanBrain.handle_user_message] CALLING_develop_bound_plan | with_updated_state")
            develop_output = await self.develop_bound_plan(
                session_state=session_state,
                draft_plan=draft_plan,
                task_master_catalogue=task_master_catalogue,
                tool_registry=tool_registry
            )
            
            logger.debug(f"[BoundedPlanBrain.handle_user_message] DEVELOP_OUTPUT | plan_readiness={develop_output.plan_readiness}, blockers={len(develop_output.bound_plan_spec.get('blockers', []))}, has_next_input={develop_output.next_input_request is not None}")
            
            # 4. Call Presenter LLM to render user-facing message
            logger.debug(f"[BoundedPlanBrain.handle_user_message] CALLING_PRESENTER_LLM")
            presenter_message = await self._call_presenter_llm(
                bound_plan_spec=develop_output.bound_plan_spec,
                session_id=session_state.session_id,
                user_id=user_id
            )
            
            logger.debug(f"[BoundedPlanBrain.handle_user_message] PRESENTER_RESPONSE | message_length={len(presenter_message.get('message', ''))}, has_question={bool(presenter_message.get('question'))}")
            
            # 5. Update session state
            session_state.last_bound_plan_spec = develop_output.bound_plan_spec
            session_state.last_next_input_request = develop_output.next_input_request
            
            # 6. Persist updated state
            await self._persist_session_state(session_state.session_id, session_state)
            logger.debug(f"[BoundedPlanBrain.handle_user_message] STATE_PERSISTED | session_id={session_state.session_id}")
            
            # 7. Return ControllerOutput
            controller_output = ControllerOutput(
                message=presenter_message.get("message", "Processing your request..."),
                question=presenter_message.get("question"),
                plan_readiness=develop_output.plan_readiness,
                bound_plan_spec=develop_output.bound_plan_spec
            )
            
            logger.debug(f"[BoundedPlanBrain.handle_user_message] EXIT | plan_readiness={develop_output.plan_readiness}, has_question={controller_output.question is not None}")
            return controller_output
            
        except Exception as e:
            logger.error(f"[BoundedPlanBrain.handle_user_message] ERROR | error={str(e)}", exc_info=True)
            raise
    
    async def develop_bound_plan(
        self,
        session_state: SessionState,
        draft_plan: Dict[str, Any],
        task_master_catalogue: Dict[str, Any],
        tool_registry: List[Any]
    ) -> DevelopOutput:
        """
        Core method that develops BoundPlanSpec from current state.
        This is called iteratively until all blockers are resolved.
        
        Args:
            session_state: Current session state
            draft_plan: Draft plan from shaping_sessions
            task_master_catalogue: Task catalog data
            tool_registry: Available tools
        
        Returns:
            DevelopOutput with bound_plan_spec, plan_readiness, and next_input_request
        """
        logger.debug(f"[BoundedPlanBrain.develop_bound_plan] ENTRY | session_id={session_state.session_id}, draft_plan_steps={sum(len(gate.get('steps', [])) for gate in draft_plan.get('gates', []))}, tools_count={len(tool_registry)}, known_fields={len(session_state.known_fields)}")
        
        try:
            # 1. Build LLM input bundle from session_state
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] BUILDING_INPUT | known_fields={len(session_state.known_fields)}, blockers={len(session_state.last_bound_plan_spec.get('blockers', []) if session_state.last_bound_plan_spec else [])}")
            
            # 2. Retrieve prompt from prompt_manager
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] RETRIEVING_PROMPT | step=bounded_plan_builder")
            
            # Get strategy from session (default to TABULA_RASA)
            session = await self._get_session(session_state.session_id)
            strategy = session.get("consultant_strategy", "TABULA_RASA") if session else "TABULA_RASA"
            domain = "eligibility"  # Default domain
            
            prompt_data = await prompt_manager.get_prompt(
                module_name="workflow",
                domain=domain,
                mode=strategy,
                step="bounded_plan_builder",
                session_id=session_state.session_id
            )
            
            if not prompt_data:
                logger.warning(f"[BoundedPlanBrain.develop_bound_plan] PROMPT_NOT_FOUND | using_fallback")
                # Fallback: create basic bound plan spec
                return self._create_fallback_bound_plan_spec(draft_plan, session_state)
            
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] PROMPT_RETRIEVED | prompt_config_keys={list(prompt_data.get('config', {}).keys())}")
            
            # 3. Build prompt with PromptBuilder
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] BUILDING_PROMPT | using_PromptBuilder")
            pb = PromptBuilder()
            pb.build_from_config(prompt_data["config"], context={
                "draft_plan": draft_plan,
                "task_master_catalogue": task_master_catalogue,
                "tool_registry": [self._tool_to_dict(t) for t in tool_registry],
                "known_fields": list(session_state.known_fields),
                "known_context": session_state.known_context,
                "user_preferences": session_state.user_preferences,
                "granted_permissions": list(session_state.granted_permissions),
                "last_bound_plan_spec": session_state.last_bound_plan_spec,
                "last_next_input_request": session_state.last_next_input_request
            })
            
            # Add dynamic context
            pb.add_context("DRAFT_PLAN", json.dumps(draft_plan, indent=2))
            pb.add_context("KNOWN_FIELDS", json.dumps(list(session_state.known_fields), indent=2))
            pb.add_context("KNOWN_CONTEXT", json.dumps(session_state.known_context, indent=2))
            pb.add_context("TOOL_REGISTRY", json.dumps([self._tool_to_dict(t) for t in tool_registry], indent=2))
            
            system_prompt = pb.build()
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] PROMPT_BUILT | system_prompt_length={len(system_prompt)}")
            
            # 4. Get model context from config_manager
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] GETTING_MODEL_CONTEXT | module=workflow")
            user_id = session.get("user_id") if session else None
            model_context = await config_manager.resolve_app_context("workflow", user_id)
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] MODEL_CONTEXT_RETRIEVED | model_id={model_context.get('model_id') if model_context else 'None'}")
            
            # 5. Call LLM via llm_service.generate_text()
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] CALLING_LLM | prompt_length={len(system_prompt)}")
            user_query = "Generate a BoundPlanSpec based on the draft plan and current session state."
            
            llm_response = await llm_service.generate_text(
                prompt=user_query,
                system_instruction=system_prompt,
                model_context=model_context,
                generation_config=prompt_data.get("generation_config", {}),
                return_metadata=False
            )
            
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] LLM_RESPONSE | response_length={len(llm_response)}, first_100_chars={llm_response[:100] if llm_response else 'None'}")
            
            # 6. Parse and validate JSON output
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] PARSING_JSON | starting_parse")
            bound_plan_spec = self._parse_bound_plan_response(llm_response)
            
            # Validate schema_version
            if bound_plan_spec.get("meta", {}).get("schema_version") != "BoundPlanSpec_v1":
                logger.warning(f"[BoundedPlanBrain.develop_bound_plan] VALIDATION_FAILED | schema_version={bound_plan_spec.get('meta', {}).get('schema_version')}, expected=BoundPlanSpec_v1")
                # Try to fix or use fallback
                bound_plan_spec["meta"]["schema_version"] = "BoundPlanSpec_v1"
            
            # Validate selected_tool keys exist in tool_registry
            tool_names = {self._get_tool_name(t) for t in tool_registry}
            for step in bound_plan_spec.get("steps", []):
                selected_tool = step.get("selected_tool")
                if selected_tool and selected_tool not in tool_names:
                    logger.warning(f"[BoundedPlanBrain.develop_bound_plan] VALIDATION_FAILED | step={step.get('id')}, selected_tool={selected_tool} not in registry")
                    # Remove invalid tool selection
                    step["selected_tool"] = None
            
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] JSON_PARSED | schema_version={bound_plan_spec.get('meta', {}).get('schema_version')}, steps_count={len(bound_plan_spec.get('steps', []))}, blockers_count={len(bound_plan_spec.get('blockers', []))}")
            
            # 7. Handle tool_ambiguity blocker if exists
            blockers = bound_plan_spec.get("blockers", [])
            tool_ambiguity_blockers = [b for b in blockers if b.get("type") == "tool_ambiguity"]
            
            if tool_ambiguity_blockers:
                logger.debug(f"[BoundedPlanBrain.develop_bound_plan] TOOL_AMBIGUITY_DETECTED | count={len(tool_ambiguity_blockers)}")
                await self._resolve_tool_ambiguity(
                    bound_plan_spec=bound_plan_spec,
                    tool_ambiguity_blockers=tool_ambiguity_blockers,
                    tool_registry=tool_registry,
                    session_id=session_state.session_id,
                    user_id=user_id
                )
            
            # 8. Determine plan_readiness
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] DETERMINING_READINESS | analyzing_blockers")
            plan_readiness = self._determine_plan_readiness(bound_plan_spec, blockers)
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] READINESS_DETERMINED | status={plan_readiness}")
            
            # 9. Extract next_input_request (highest priority blocker)
            next_input_request = self._extract_next_input_request(blockers)
            if next_input_request:
                logger.debug(f"[BoundedPlanBrain.develop_bound_plan] NEXT_INPUT_REQUEST | blocker_type={next_input_request.get('blocker_type')}, writes_to={next_input_request.get('writes_to', [])}")
            
            logger.debug(f"[BoundedPlanBrain.develop_bound_plan] EXIT | plan_readiness={plan_readiness}, blockers={len(blockers)}, has_next_input={next_input_request is not None}")
            
            return DevelopOutput(
                bound_plan_spec=bound_plan_spec,
                plan_readiness=plan_readiness,
                next_input_request=next_input_request
            )
            
        except Exception as e:
            logger.error(f"[BoundedPlanBrain.develop_bound_plan] ERROR | error={str(e)}", exc_info=True)
            raise
    
    async def _fetch_patient_profile(self, user_name_or_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch patient profile data from user profile manager API endpoints.
        
        Args:
            user_name_or_id: Patient name or ID
        
        Returns:
            Merged patient profile data or None if not found
        """
        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] ENTRY | identifier={user_name_or_id}")
        
        try:
            import httpx
            
            base_url = "http://localhost:8000"  # API base URL
            
            # 1. Search for patient
            logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] SEARCHING_PATIENT | query={user_name_or_id}")
            search_url = f"{base_url}/api/user-profiles/search"
            
            async with httpx.AsyncClient() as client:
                try:
                    search_response = await client.get(search_url, params={"name": user_name_or_id})
                    logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] SEARCH_RESPONSE | status={search_response.status_code}")
                    
                    if search_response.status_code == 200:
                        search_results = search_response.json()
                        patients = search_results.get("patients", [])
                        
                        if not patients:
                            logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] PATIENT_NOT_FOUND | no_results")
                            return None
                        
                        # Use first match
                        patient_id = patients[0].get("patient_id")
                        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | patient_id={patient_id}")
                    else:
                        logger.warning(f"[BoundedPlanBrain._fetch_patient_profile] SEARCH_FAILED | status={search_response.status_code}")
                        return None
                except Exception as e:
                    logger.warning(f"[BoundedPlanBrain._fetch_patient_profile] SEARCH_ERROR | error={str(e)}")
                    return None
                
                # 2. Fetch all views
                merged_profile = {"patient_id": patient_id}
                views_retrieved = []
                
                # EMR view
                logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] FETCHING_EMR_VIEW | patient_id={patient_id}")
                try:
                    emr_response = await client.get(f"{base_url}/api/user-profiles/{patient_id}/emr")
                    if emr_response.status_code == 200:
                        emr_data = emr_response.json()
                        merged_profile["emr_data"] = emr_data
                        views_retrieved.append("emr")
                        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | keys={list(emr_data.keys())}")
                    else:
                        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_UNAVAILABLE | status={emr_response.status_code}")
                except Exception as e:
                    logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_ERROR | error={str(e)}")
                
                # System view
                logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] FETCHING_SYSTEM_VIEW | patient_id={patient_id}")
                try:
                    system_response = await client.get(f"{base_url}/api/user-profiles/{patient_id}/system")
                    if system_response.status_code == 200:
                        system_data = system_response.json()
                        merged_profile["system_data"] = system_data
                        views_retrieved.append("system")
                        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_RETRIEVED | keys={list(system_data.keys())}")
                    else:
                        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_UNAVAILABLE | status={system_response.status_code}")
                except Exception as e:
                    logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_ERROR | error={str(e)}")
                
                # Health plan view
                logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] FETCHING_HEALTH_PLAN_VIEW | patient_id={patient_id}")
                try:
                    health_plan_response = await client.get(f"{base_url}/api/user-profiles/{patient_id}/health-plan")
                    if health_plan_response.status_code == 200:
                        health_plan_data = health_plan_response.json()
                        merged_profile["health_plan_data"] = health_plan_data
                        views_retrieved.append("health_plan")
                        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_RETRIEVED | keys={list(health_plan_data.keys())}")
                    else:
                        logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_UNAVAILABLE | status={health_plan_response.status_code}")
                except Exception as e:
                    logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_ERROR | error={str(e)}")
                
                # Extract key fields from merged data
                extracted_fields = {}
                
                # From system_data (demographics)
                if "system_data" in merged_profile:
                    sys_data = merged_profile["system_data"]
                    demographics = sys_data.get("demographics", {})
                    extracted_fields.update({
                        "patient_id": demographics.get("patient_id") or patient_id,
                        "patient_name": demographics.get("name"),
                        "date_of_birth": demographics.get("dob"),
                        "gender": demographics.get("gender"),
                        "address": demographics.get("address"),
                        "phone": demographics.get("phone"),
                        "email": demographics.get("email")
                    })
                
                # From health_plan_data (insurance)
                if "health_plan_data" in merged_profile:
                    hp_data = merged_profile["health_plan_data"]
                    extracted_fields.update({
                        "insurance_carrier": hp_data.get("carrier"),
                        "member_id": hp_data.get("member_id"),
                        "group_number": hp_data.get("group"),
                        "coverage_status": hp_data.get("eligibility", {}).get("status")
                    })
                
                logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] DATA_MERGED | views={views_retrieved}, extracted_fields={list(extracted_fields.keys())}")
                
                # Add full profile data
                extracted_fields["patient_profile"] = merged_profile
                
                logger.debug(f"[BoundedPlanBrain._fetch_patient_profile] EXIT | fields_count={len(extracted_fields)}")
                return extracted_fields
                
        except Exception as e:
            logger.error(f"[BoundedPlanBrain._fetch_patient_profile] ERROR | error={str(e)}", exc_info=True)
            return None
    
    # Helper methods
    
    def _parse_bound_plan_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM JSON response - handles markdown code blocks and extra text."""
        logger.debug(f"[BoundedPlanBrain._parse_bound_plan_response] ENTRY | response_length={len(llm_response)}")
        
        # Reuse the robust parsing logic from planning_phase.py
        def extract_json_with_brace_counting(text: str) -> Optional[str]:
            """Extract JSON object from text using brace counting."""
            start_idx = text.find('{')
            if start_idx == -1:
                return None
            
            brace_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start_idx:i+1]
            return None
        
        # Step 1: Try to extract JSON from markdown code blocks
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        code_block_match = re.search(code_block_pattern, llm_response, re.DOTALL)
        if code_block_match:
            code_block_content = code_block_match.group(1).strip()
            logger.debug(f"[BoundedPlanBrain._parse_bound_plan_response] FOUND_CODE_BLOCK | length={len(code_block_content)}")
            
            try:
                parsed = json.loads(code_block_content)
                logger.debug(f"[BoundedPlanBrain._parse_bound_plan_response] PARSED_FROM_CODE_BLOCK | success")
                return parsed
            except json.JSONDecodeError:
                logger.debug(f"[BoundedPlanBrain._parse_bound_plan_response] CODE_BLOCK_PARSE_FAILED | trying_brace_counting")
                json_candidate = extract_json_with_brace_counting(code_block_content)
                if json_candidate:
                    try:
                        parsed = json.loads(json_candidate)
                        logger.debug(f"[BoundedPlanBrain._parse_bound_plan_response] PARSED_WITH_BRACE_COUNTING | success")
                        return parsed
                    except json.JSONDecodeError as e:
                        logger.warning(f"[BoundedPlanBrain._parse_bound_plan_response] BRACE_COUNTING_FAILED | error={str(e)}")
        
        # Step 2: Try brace counting on full response
        json_candidate = extract_json_with_brace_counting(llm_response)
        if json_candidate:
            try:
                parsed = json.loads(json_candidate)
                logger.debug(f"[BoundedPlanBrain._parse_bound_plan_response] PARSED_FULL_RESPONSE | success")
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"[BoundedPlanBrain._parse_bound_plan_response] FULL_RESPONSE_PARSE_FAILED | error={str(e)}")
        
        # Step 3: Try parsing entire response as JSON
        try:
            parsed = json.loads(llm_response.strip())
            logger.debug(f"[BoundedPlanBrain._parse_bound_plan_response] PARSED_DIRECT | success")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"[BoundedPlanBrain._parse_bound_plan_response] ALL_PARSING_FAILED | error={str(e)}")
            # Return default structure
            return {
                "meta": {
                    "plan_id": "unknown",
                    "workflow": "unknown",
                    "phase": "BOUND",
                    "schema_version": "BoundPlanSpec_v1"
                },
                "steps": [],
                "blockers": [{
                    "type": "missing_information",
                    "step_id": None,
                    "message": "Failed to parse LLM response",
                    "priority": 5
                }],
                "plan_readiness": "BLOCKED",
                "next_input_request": None
            }
    
    def _determine_plan_readiness(self, bound_plan_spec: Dict[str, Any], blockers: List[Dict[str, Any]]) -> str:
        """Determine plan readiness based on blockers."""
        logger.debug(f"[BoundedPlanBrain._determine_plan_readiness] ENTRY | blockers_count={len(blockers)}")
        
        if not blockers:
            logger.debug(f"[BoundedPlanBrain._determine_plan_readiness] READY | no_blockers")
            return "READY_FOR_COMPILATION"
        
        # Check for critical blockers
        critical_blocker_types = ["tool_gap", "policy_conflict"]
        has_critical = any(b.get("type") in critical_blocker_types for b in blockers)
        
        if has_critical:
            logger.debug(f"[BoundedPlanBrain._determine_plan_readiness] BLOCKED | critical_blockers_present")
            return "BLOCKED"
        
        # Check if there's a next_input_request
        next_input_request = self._extract_next_input_request(blockers)
        if next_input_request:
            logger.debug(f"[BoundedPlanBrain._determine_plan_readiness] NEEDS_INPUT | has_next_input_request")
            return "NEEDS_INPUT"
        
        logger.debug(f"[BoundedPlanBrain._determine_plan_readiness] READY | no_critical_blockers")
        return "READY_FOR_COMPILATION"
    
    def _extract_next_input_request(self, blockers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract next input request from highest priority blocker."""
        logger.debug(f"[BoundedPlanBrain._extract_next_input_request] ENTRY | blockers_count={len(blockers)}")
        
        if not blockers:
            logger.debug(f"[BoundedPlanBrain._extract_next_input_request] EXIT | no_blockers")
            return None
        
        # Blocker priority order
        priority_order = {
            "missing_preference": 1,
            "missing_permission": 2,
            "tool_gap": 3,
            "tool_ambiguity": 4,
            "missing_information": 5,
            "timeline_risk": 6,
            "human_required": 7,
            "other": 8
        }
        
        # Sort blockers by priority
        sorted_blockers = sorted(blockers, key=lambda b: priority_order.get(b.get("type", "other"), 8))
        highest_priority = sorted_blockers[0]
        
        logger.debug(f"[BoundedPlanBrain._extract_next_input_request] PRIORITY_SELECTED | blocker_type={highest_priority.get('type')}, step_id={highest_priority.get('step_id')}")
        
        # Build next_input_request from blocker
        next_input_request = {
            "blocker_type": highest_priority.get("type"),
            "step_id": highest_priority.get("step_id"),
            "message": highest_priority.get("message", "Please provide additional information"),
            "writes_to": highest_priority.get("writes_to", [])
        }
        
        logger.debug(f"[BoundedPlanBrain._extract_next_input_request] EXIT | writes_to={next_input_request.get('writes_to')}")
        return next_input_request
    
    async def _resolve_tool_ambiguity(
        self,
        bound_plan_spec: Dict[str, Any],
        tool_ambiguity_blockers: List[Dict[str, Any]],
        tool_registry: List[Any],
        session_id: int,
        user_id: Optional[str]
    ) -> None:
        """Resolve tool ambiguity using tie-breaker prompt."""
        logger.debug(f"[BoundedPlanBrain._resolve_tool_ambiguity] ENTRY | blockers_count={len(tool_ambiguity_blockers)}")
        
        try:
            # Get tie-breaker prompt
            session = await self._get_session(session_id)
            strategy = session.get("consultant_strategy", "TABULA_RASA") if session else "TABULA_RASA"
            
            prompt_data = await prompt_manager.get_prompt(
                module_name="workflow",
                domain="eligibility",
                mode=strategy,
                step="tool_tiebreaker",
                session_id=session_id
            )
            
            if not prompt_data:
                logger.warning(f"[BoundedPlanBrain._resolve_tool_ambiguity] PROMPT_NOT_FOUND | using_fallback")
                return
            
            # Build prompt with ambiguity context
            pb = PromptBuilder()
            pb.build_from_config(prompt_data["config"], context={
                "bound_plan_spec": bound_plan_spec,
                "tool_ambiguity_blockers": tool_ambiguity_blockers,
                "tool_registry": [self._tool_to_dict(t) for t in tool_registry]
            })
            
            system_prompt = pb.build()
            user_query = "Resolve tool ambiguity by selecting the most appropriate tool for each ambiguous step."
            
            model_context = await config_manager.resolve_app_context("workflow", user_id)
            llm_response = await llm_service.generate_text(
                prompt=user_query,
                system_instruction=system_prompt,
                model_context=model_context,
                generation_config=prompt_data.get("generation_config", {}),
                return_metadata=False
            )
            
            # Parse response and patch selected_tool_key into bound_plan_spec
            tie_breaker_result = self._parse_bound_plan_response(llm_response)
            tool_selections = tie_breaker_result.get("tool_selections", [])
            
            for selection in tool_selections:
                step_id = selection.get("step_id")
                selected_tool = selection.get("selected_tool")
                
                # Find step and update
                for step in bound_plan_spec.get("steps", []):
                    if step.get("id") == step_id:
                        step["selected_tool"] = selected_tool
                        logger.debug(f"[BoundedPlanBrain._resolve_tool_ambiguity] TOOL_SELECTED | step_id={step_id}, tool={selected_tool}")
                        break
            
            logger.debug(f"[BoundedPlanBrain._resolve_tool_ambiguity] EXIT | selections_made={len(tool_selections)}")
            
        except Exception as e:
            logger.error(f"[BoundedPlanBrain._resolve_tool_ambiguity] ERROR | error={str(e)}", exc_info=True)
    
    async def _call_presenter_llm(
        self,
        bound_plan_spec: Dict[str, Any],
        session_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """Call presenter LLM to render user-facing message."""
        logger.debug(f"[BoundedPlanBrain._call_presenter_llm] ENTRY | session_id={session_id}")
        
        try:
            session = await self._get_session(session_id)
            strategy = session.get("consultant_strategy", "TABULA_RASA") if session else "TABULA_RASA"
            
            prompt_data = await prompt_manager.get_prompt(
                module_name="workflow",
                domain="eligibility",
                mode=strategy,
                step="bounded_plan_presenter",
                session_id=session_id
            )
            
            if not prompt_data:
                logger.warning(f"[BoundedPlanBrain._call_presenter_llm] PROMPT_NOT_FOUND | using_fallback")
                return {
                    "message": "I'm working on your workflow plan. " + (bound_plan_spec.get("next_input_request", {}).get("message", "Please provide the requested information.") if bound_plan_spec.get("next_input_request") else "Processing..."),
                    "question": bound_plan_spec.get("next_input_request", {}).get("message") if bound_plan_spec.get("next_input_request") else None
                }
            
            pb = PromptBuilder()
            pb.build_from_config(prompt_data["config"], context={
                "bound_plan_spec": bound_plan_spec,
                "blockers": bound_plan_spec.get("blockers", []),
                "next_input_request": bound_plan_spec.get("next_input_request")
            })
            
            system_prompt = pb.build()
            user_query = "Generate a user-friendly message and question based on the current bound plan spec."
            
            model_context = await config_manager.resolve_app_context("workflow", user_id)
            llm_response = await llm_service.generate_text(
                prompt=user_query,
                system_instruction=system_prompt,
                model_context=model_context,
                generation_config=prompt_data.get("generation_config", {}),
                return_metadata=False
            )
            
            # Parse JSON response
            presenter_result = self._parse_bound_plan_response(llm_response)
            
            logger.debug(f"[BoundedPlanBrain._call_presenter_llm] EXIT | has_message={bool(presenter_result.get('message'))}, has_question={bool(presenter_result.get('question'))}")
            
            return {
                "message": presenter_result.get("message", "Processing your request..."),
                "question": presenter_result.get("question")
            }
            
        except Exception as e:
            logger.error(f"[BoundedPlanBrain._call_presenter_llm] ERROR | error={str(e)}", exc_info=True)
            return {
                "message": "I'm working on your workflow plan. Please provide the requested information.",
                "question": bound_plan_spec.get("next_input_request", {}).get("message") if bound_plan_spec.get("next_input_request") else None
            }
    
    def _create_fallback_bound_plan_spec(
        self,
        draft_plan: Dict[str, Any],
        session_state: SessionState
    ) -> DevelopOutput:
        """Create fallback bound plan spec when prompt is not found."""
        logger.debug(f"[BoundedPlanBrain._create_fallback_bound_plan_spec] ENTRY | creating_fallback")
        
        # Convert draft plan steps to bound plan steps
        steps = []
        blockers = []
        
        for gate in draft_plan.get("gates", []):
            for step in gate.get("steps", []):
                step_id = step.get("id", f"step_{len(steps) + 1}")
                steps.append({
                    "id": step_id,
                    "description": step.get("description", ""),
                    "selected_tool": None,
                    "tool_parameters": {},
                    "depends_on": step.get("depends_on", [])
                })
                
                # Add missing_information blocker if inputs are missing
                inputs = step.get("inputs", [])
                missing_inputs = [inp for inp in inputs if inp not in session_state.known_fields]
                if missing_inputs:
                    blockers.append({
                        "type": "missing_information",
                        "step_id": step_id,
                        "message": f"Missing information: {', '.join(missing_inputs)}",
                        "priority": 5,
                        "writes_to": missing_inputs
                    })
        
        bound_plan_spec = {
            "meta": {
                "plan_id": draft_plan.get("name", "unknown"),
                "workflow": draft_plan.get("goal", "unknown"),
                "phase": "BOUND",
                "schema_version": "BoundPlanSpec_v1"
            },
            "steps": steps,
            "blockers": blockers,
            "plan_readiness": "NEEDS_INPUT" if blockers else "READY_FOR_COMPILATION",
            "next_input_request": self._extract_next_input_request(blockers)
        }
        
        logger.debug(f"[BoundedPlanBrain._create_fallback_bound_plan_spec] EXIT | steps={len(steps)}, blockers={len(blockers)}")
        
        return DevelopOutput(
            bound_plan_spec=bound_plan_spec,
            plan_readiness=bound_plan_spec["plan_readiness"],
            next_input_request=bound_plan_spec["next_input_request"]
        )
    
    def _tool_to_dict(self, tool: Any) -> Dict[str, Any]:
        """Convert tool to dictionary representation."""
        try:
            schema = tool.define_schema()
            return {
                "name": schema.name,
                "description": schema.description,
                "parameters": [p.dict() for p in schema.parameters] if hasattr(schema, "parameters") else []
            }
        except Exception:
            return {"name": str(tool), "description": "", "parameters": []}
    
    def _get_tool_name(self, tool: Any) -> str:
        """Get tool name from tool object."""
        try:
            schema = tool.define_schema()
            return schema.name
        except Exception:
            return str(tool)
    
    async def _get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session from database."""
        logger.debug(f"[BoundedPlanBrain._get_session] ENTRY | session_id={session_id}")
        
        try:
            query = "SELECT * FROM shaping_sessions WHERE id = :id"
            row = await database.fetch_one(query, {"id": session_id})
            
            if row:
                session_dict = dict(row)
                # Parse JSONB fields
                if isinstance(session_dict.get("draft_plan"), str):
                    session_dict["draft_plan"] = json.loads(session_dict["draft_plan"])
                if isinstance(session_dict.get("transcript"), str):
                    session_dict["transcript"] = json.loads(session_dict["transcript"])
                
                logger.debug(f"[BoundedPlanBrain._get_session] EXIT | session_found")
                return session_dict
            
            logger.debug(f"[BoundedPlanBrain._get_session] EXIT | session_not_found")
            return None
            
        except Exception as e:
            logger.error(f"[BoundedPlanBrain._get_session] ERROR | error={str(e)}", exc_info=True)
            return None
    
    async def _persist_session_state(self, session_id: int, session_state: SessionState) -> None:
        """Persist session state to database."""
        logger.debug(f"[BoundedPlanBrain._persist_session_state] ENTRY | session_id={session_id}")
        
        try:
            state_dict = session_state.to_dict()
            
            query = """
                UPDATE shaping_sessions 
                SET bounded_plan_state = :state, updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """
            
            await database.execute(query, {
                "id": session_id,
                "state": json.dumps(state_dict)
            })
            
            # Also persist bound_plan_spec if available
            if session_state.last_bound_plan_spec:
                query2 = """
                    UPDATE shaping_sessions 
                    SET bound_plan_spec = :spec, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """
                await database.execute(query2, {
                    "id": session_id,
                    "spec": json.dumps(session_state.last_bound_plan_spec)
                })
            
            logger.debug(f"[BoundedPlanBrain._persist_session_state] EXIT | state_persisted")
            
        except Exception as e:
            logger.error(f"[BoundedPlanBrain._persist_session_state] ERROR | error={str(e)}", exc_info=True)


# Singleton instance
bounded_plan_brain = BoundedPlanBrain()



