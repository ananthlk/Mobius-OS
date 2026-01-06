"""
Centralized JSON Parser Utility for LLM Responses

Provides a unified interface for extracting and querying JSON from LLM outputs.
Any service can use this to parse and extract specific fields from JSON responses.

Usage:
    parser = LLMResponseParser()
    
    # Extract JSON from text
    data = parser.extract_json(response_text)
    
    # Query specific fields
    result = parser.get_fields(data, ['plan_name', 'completion_status.is_complete', 'questions'])
    
    # Or use the convenience method
    result = parser.parse_and_query(response_text, ['plan_name', 'steps'])
"""

import json
import re
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass

logger = logging.getLogger("nexus.core.json_parser")


@dataclass
class ParseResult:
    """Result of JSON parsing operation."""
    data: Optional[Dict[str, Any]]
    success: bool
    error: Optional[str] = None
    normalized: bool = False
    original_format: Optional[str] = None


class LLMResponseParser:
    """
    Centralized JSON parser for LLM responses.
    
    Handles:
    - JSON extraction from text (markdown, thinking tags, etc.)
    - Format normalization (status/collected → plan_name/steps)
    - Field querying with dot notation
    - Extensible for future enhancements (validation, schema matching, etc.)
    """
    
    def __init__(self):
        self.normalizers = {
            'consultant_response': self._normalize_consultant_response,
            'planner_response': self._normalize_planner_response,
            # Add more normalizers as needed
        }
    
    def extract_json(
        self, 
        text: str, 
        normalize: bool = True,
        format_hint: Optional[str] = None
    ) -> ParseResult:
        """
        Extracts JSON from text response.
        
        Args:
            text: Raw LLM response text
            normalize: Whether to normalize to standard format
            format_hint: Hint about expected format ('consultant_response', 'planner_response', etc.)
        
        Returns:
            ParseResult with extracted/normalized data
        """
        if not text:
            return ParseResult(None, False, "Empty input")
        
        # Step 1: Remove thinking tags
        cleaned = self._remove_thinking_tags(text)
        
        # Step 2: Extract JSON
        json_str = self._extract_json_string(cleaned)
        
        if not json_str:
            return ParseResult(None, False, "No JSON object found")
        
        # Step 3: Parse JSON
        try:
            data = json.loads(json_str)
            
            # Step 4: Normalize if requested
            original_format = self._detect_format(data)
            if normalize and format_hint:
                normalizer = self.normalizers.get(format_hint)
                if normalizer:
                    data = normalizer(data)
                    normalized = True
                else:
                    normalized = False
            elif normalize:
                # Auto-detect and normalize
                if original_format == 'status_collected':
                    data = self._normalize_consultant_response(data)
                    normalized = True
                else:
                    normalized = False
            else:
                normalized = False
            
            return ParseResult(
                data=data,
                success=True,
                normalized=normalized,
                original_format=original_format
            )
            
        except json.JSONDecodeError as e:
            return ParseResult(None, False, f"JSON parse error: {str(e)}")
        except Exception as e:
            return ParseResult(None, False, f"Parse error: {str(e)}")
    
    def get_fields(
        self, 
        data: Dict[str, Any], 
        fields: List[str],
        default: Any = None
    ) -> Dict[str, Any]:
        """
        Query specific fields from parsed JSON using dot notation.
        
        Args:
            data: Parsed JSON dictionary
            fields: List of field paths (supports dot notation, e.g., 'completion_status.is_complete')
            default: Default value if field not found
        
        Returns:
            Dictionary with requested fields
        
        Example:
            data = {'plan_name': 'Test', 'completion_status': {'is_complete': True}}
            result = parser.get_fields(data, ['plan_name', 'completion_status.is_complete'])
            # Returns: {'plan_name': 'Test', 'completion_status.is_complete': True}
        """
        result = {}
        
        for field_path in fields:
            value = self._get_nested_field(data, field_path, default)
            result[field_path] = value
        
        return result
    
    def parse_and_query(
        self,
        text: str,
        fields: List[str],
        normalize: bool = True,
        format_hint: Optional[str] = None,
        default: Any = None
    ) -> Tuple[ParseResult, Dict[str, Any]]:
        """
        Convenience method: Extract JSON and query fields in one call.
        
        Args:
            text: Raw LLM response text
            fields: List of field paths to extract
            normalize: Whether to normalize format
            format_hint: Hint about expected format
            default: Default value for missing fields
        
        Returns:
            Tuple of (ParseResult, queried_fields_dict)
        """
        parse_result = self.extract_json(text, normalize=normalize, format_hint=format_hint)
        
        if parse_result.success and parse_result.data:
            queried = self.get_fields(parse_result.data, fields, default)
            return parse_result, queried
        else:
            return parse_result, {}
    
    # ============================================================================
    # Private Helper Methods
    # ============================================================================
    
    def _remove_thinking_tags(self, text: str) -> str:
        """Remove <thinking>...</thinking> tags."""
        return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()
    
    def _extract_json_string(self, text: str) -> Optional[str]:
        """Extract JSON string from text using multiple strategies."""
        # Strategy 1: Markdown code blocks
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1)
            # Clean up markdown remnants
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'^```\s*', '', json_str)
            json_str = re.sub(r'```\s*$', '', json_str)
            return json_str.strip()
        
        # Strategy 2: JSON with common keys
        json_match = re.search(
            r'\{[^{}]*(?:"plan_name"|"steps"|"completion_status"|"status"|"collected")[^{}]*\}',
            text,
            re.DOTALL
        )
        if json_match:
            return json_match.group(0)
        
        # Strategy 3: Any JSON object (broader match)
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return None
    
    def _detect_format(self, data: Dict[str, Any]) -> str:
        """Detect the format of the JSON structure."""
        if "status" in data or "collected" in data:
            return "status_collected"
        elif "plan_name" in data or "steps" in data:
            return "consultant_standard"
        elif "name" in data and "goal" in data:
            return "planner_standard"
        else:
            return "unknown"
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str, default: Any = None) -> Any:
        """Get nested field using dot notation."""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        
        return value if value is not None else default
    
    # ============================================================================
    # Normalizers
    # ============================================================================
    
    def _normalize_consultant_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize consultant response to standard format.
        
        Handles:
        - status/collected → plan_name/steps/completion_status
        - status.complete → completion_status.is_complete
        - status.next_query → questions array
        """
        normalized = {}
        
        # If already in standard format, return as-is (but ensure completion_status is complete)
        if "plan_name" in data and "completion_status" in data:
            # Ensure completion_status has all required fields
            completion = data.get("completion_status", {})
            if not isinstance(completion, dict):
                completion = {}
            
            completion.setdefault("is_complete", False)
            completion.setdefault("completion_reason", "still_in_progress")
            completion.setdefault("ready_for_handoff", False)
            completion.setdefault("completion_summary", None)
            
            data["completion_status"] = completion
            return data
        
        # Handle status/collected format
        if "status" in data or "collected" in data:
            status = data.get("status", {})
            collected = data.get("collected", {})
            
            # Map status.next_query to questions
            questions = []
            if status.get("next_query"):
                questions.append(status["next_query"])
            if "questions" in data:
                questions.extend(data["questions"])
            normalized["questions"] = questions
            
            # Map collected fields to missing_information
            missing = []
            if collected.get("use_case") is None:
                missing.append("Use case (billing, clinical, financial, other)")
            if collected.get("data_fields") is None:
                missing.append("Required data fields")
            if collected.get("failure_process") is None:
                missing.append("Edge case handling (what happens if not found)")
            normalized["missing_information"] = missing
            
            # Normalize completion_status
            normalized["completion_status"] = {
                "is_complete": status.get("complete", False),
                "completion_reason": "still_in_progress" if not status.get("complete") else "user_explicitly_confirmed",
                "ready_for_handoff": status.get("complete", False),
                "completion_summary": None
            }
            
            # Set defaults
            normalized["plan_name"] = data.get("plan_name", "Workflow Name TBD")
            normalized["goal"] = data.get("goal", "To be determined")
            normalized["steps"] = data.get("steps", [])
        
        # Handle other formats or merge with existing data
        else:
            normalized = {
                "plan_name": data.get("plan_name", "Workflow Name TBD"),
                "goal": data.get("goal", "To be determined"),
                "steps": data.get("steps", []),
                "questions": data.get("questions", []),
                "missing_information": data.get("missing_information", []),
                "completion_status": data.get("completion_status", {
                    "is_complete": False,
                    "completion_reason": "still_in_progress",
                    "ready_for_handoff": False,
                    "completion_summary": None
                })
            }
        
        # Ensure completion_status has all required fields
        completion = normalized.get("completion_status", {})
        if not isinstance(completion, dict):
            completion = {}
        
        completion.setdefault("is_complete", False)
        completion.setdefault("completion_reason", "still_in_progress")
        completion.setdefault("ready_for_handoff", False)
        completion.setdefault("completion_summary", None)
        
        normalized["completion_status"] = completion
        
        return normalized
    
    def _normalize_planner_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize planner response to standard format."""
        # Add planner-specific normalization logic here
        return data


# Global instance for easy import
json_parser = LLMResponseParser()





