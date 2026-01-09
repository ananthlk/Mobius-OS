"""
Task Schema Validator

Validates task data against the task catalog schema.
Provides detailed validation errors for schema compliance.
"""
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("nexus.core.task_schema_validator")


class TaskSchemaValidator:
    """Validates task schema against the task catalog template."""
    
    # Valid enum values from the schema
    VALID_CATEGORIES = ["collect", "verify", "interpret", "notify", "escalate", "decide", "wait", "manual"]
    VALID_AUTOMATION_MODES = ["agent", "copilot", "human_led"]
    VALID_RISK_LEVELS = ["low", "medium", "high"]
    VALID_LATENCY_VALUES = ["instant", "minutes", "hours", "days"]
    VALID_RETRY_BACKOFF = ["none", "linear", "exponential"]
    VALID_INPUT_TYPES = ["choice", "text", "approval", "none"]
    VALID_STATUSES = ["draft", "active", "deprecated"]
    VALID_PHI_LEVELS = ["none", "low", "high"]
    VALID_PII_LEVELS = ["none", "low", "high"]
    VALID_CHANNELS = ["email", "sms", "phone", "portal", "none"]
    VALID_PERMISSIONS = ["patient_contact", "data_use", "external_disclosure", "billing_action", "other"]
    VALID_NOTIFY_FREQUENCIES = ["immediate", "on_blocker", "on_completion", "never"]
    VALID_ESCALATE_ON = ["timeout", "tool_failure", "missing_info", "permission_denied", "other"]
    
    def validate_task_schema(self, task_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate task data against the schema.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required top-level fields
        if "task_key" not in task_data:
            errors.append("Missing required field: task_key")
        elif not isinstance(task_data["task_key"], str) or not task_data["task_key"].strip():
            errors.append("task_key must be a non-empty string")
        
        if "name" not in task_data:
            errors.append("Missing required field: name")
        elif not isinstance(task_data["name"], str) or not task_data["name"].strip():
            errors.append("name must be a non-empty string")
        
        # Validate classification
        if "classification" in task_data:
            errors.extend(self._validate_classification(task_data["classification"]))
        
        # Validate contract
        if "contract" in task_data:
            errors.extend(self._validate_contract(task_data["contract"]))
        
        # Validate automation
        if "automation" in task_data:
            errors.extend(self._validate_automation(task_data["automation"]))
        
        # Validate tool_binding_defaults
        if "tool_binding_defaults" in task_data:
            errors.extend(self._validate_tool_binding(task_data["tool_binding_defaults"]))
        
        # Validate information
        if "information" in task_data:
            errors.extend(self._validate_information(task_data["information"]))
        
        # Validate policy
        if "policy" in task_data:
            errors.extend(self._validate_policy(task_data["policy"]))
        
        # Validate temporal
        if "temporal" in task_data:
            errors.extend(self._validate_temporal(task_data["temporal"]))
        
        # Validate escalation
        if "escalation" in task_data:
            errors.extend(self._validate_escalation(task_data["escalation"]))
        
        # Validate dependencies
        if "dependencies" in task_data:
            errors.extend(self._validate_dependencies(task_data["dependencies"]))
        
        # Validate failure
        if "failure" in task_data:
            errors.extend(self._validate_failure(task_data["failure"]))
        
        # Validate ui
        if "ui" in task_data:
            errors.extend(self._validate_ui(task_data["ui"]))
        
        # Validate governance
        if "governance" in task_data:
            errors.extend(self._validate_governance(task_data["governance"]))
        
        # Validate status
        if "status" in task_data:
            if task_data["status"] not in self.VALID_STATUSES:
                errors.append(f"status must be one of {self.VALID_STATUSES}")
        
        return (len(errors) == 0, errors)
    
    def _validate_classification(self, classification: Dict[str, Any]) -> List[str]:
        """Validate classification section."""
        errors = []
        if not isinstance(classification, dict):
            return ["classification must be a dictionary"]
        
        if "category" in classification:
            if classification["category"] not in self.VALID_CATEGORIES:
                errors.append(f"classification.category must be one of {self.VALID_CATEGORIES}")
        
        if "tags" in classification:
            if not isinstance(classification["tags"], list):
                errors.append("classification.tags must be a list")
            elif not all(isinstance(tag, str) for tag in classification["tags"]):
                errors.append("classification.tags must be a list of strings")
        
        return errors
    
    def _validate_contract(self, contract: Dict[str, Any]) -> List[str]:
        """Validate contract section."""
        errors = []
        if not isinstance(contract, dict):
            return ["contract must be a dictionary"]
        
        # Validate array fields
        for field in ["requires", "produces", "success_criteria", "preconditions", "postconditions"]:
            if field in contract:
                if not isinstance(contract[field], list):
                    errors.append(f"contract.{field} must be a list")
                elif not all(isinstance(item, str) for item in contract[field]):
                    errors.append(f"contract.{field} must be a list of strings")
        
        return errors
    
    def _validate_automation(self, automation: Dict[str, Any]) -> List[str]:
        """Validate automation section."""
        errors = []
        if not isinstance(automation, dict):
            return ["automation must be a dictionary"]
        
        if "default_mode" in automation:
            if automation["default_mode"] not in self.VALID_AUTOMATION_MODES:
                errors.append(f"automation.default_mode must be one of {self.VALID_AUTOMATION_MODES}")
        
        if "risk_level" in automation:
            if automation["risk_level"] not in self.VALID_RISK_LEVELS:
                errors.append(f"automation.risk_level must be one of {self.VALID_RISK_LEVELS}")
        
        if "confidence_threshold" in automation:
            threshold = automation["confidence_threshold"]
            if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 1):
                errors.append("automation.confidence_threshold must be a number between 0 and 1")
        
        if "agentic_allowed" in automation:
            if not isinstance(automation["agentic_allowed"], bool):
                errors.append("automation.agentic_allowed must be a boolean")
        
        if "requires_human_decision" in automation:
            if not isinstance(automation["requires_human_decision"], bool):
                errors.append("automation.requires_human_decision must be a boolean")
        
        if "requires_human_action" in automation:
            if not isinstance(automation["requires_human_action"], bool):
                errors.append("automation.requires_human_action must be a boolean")
        
        if "non_agentic_reasons" in automation:
            if not isinstance(automation["non_agentic_reasons"], list):
                errors.append("automation.non_agentic_reasons must be a list")
            elif not all(isinstance(item, str) for item in automation["non_agentic_reasons"]):
                errors.append("automation.non_agentic_reasons must be a list of strings")
        
        return errors
    
    def _validate_tool_binding(self, tool_binding: Dict[str, Any]) -> List[str]:
        """Validate tool_binding_defaults section."""
        errors = []
        if not isinstance(tool_binding, dict):
            return ["tool_binding_defaults must be a dictionary"]
        
        if "candidate_tool_keys" in tool_binding:
            if not isinstance(tool_binding["candidate_tool_keys"], list):
                errors.append("tool_binding_defaults.candidate_tool_keys must be a list")
            elif not all(isinstance(item, str) for item in tool_binding["candidate_tool_keys"]):
                errors.append("tool_binding_defaults.candidate_tool_keys must be a list of strings")
        
        if "tool_required" in tool_binding:
            if not isinstance(tool_binding["tool_required"], bool):
                errors.append("tool_binding_defaults.tool_required must be a boolean")
        
        if "binding_hints" in tool_binding:
            if not isinstance(tool_binding["binding_hints"], dict):
                errors.append("tool_binding_defaults.binding_hints must be a dictionary")
            else:
                hints = tool_binding["binding_hints"]
                if "prefer_tools" in hints and not isinstance(hints["prefer_tools"], list):
                    errors.append("tool_binding_defaults.binding_hints.prefer_tools must be a list")
                if "avoid_tools" in hints and not isinstance(hints["avoid_tools"], list):
                    errors.append("tool_binding_defaults.binding_hints.avoid_tools must be a list")
        
        return errors
    
    def _validate_information(self, information: Dict[str, Any]) -> List[str]:
        """Validate information section."""
        errors = []
        if not isinstance(information, dict):
            return ["information must be a dictionary"]
        
        if "required_fields" in information:
            if not isinstance(information["required_fields"], list):
                errors.append("information.required_fields must be a list")
            elif not all(isinstance(item, str) for item in information["required_fields"]):
                errors.append("information.required_fields must be a list of strings")
        
        if "optional_fields" in information:
            if not isinstance(information["optional_fields"], list):
                errors.append("information.optional_fields must be a list")
            elif not all(isinstance(item, str) for item in information["optional_fields"]):
                errors.append("information.optional_fields must be a list of strings")
        
        if "confidence_user_has_fields" in information:
            conf = information["confidence_user_has_fields"]
            if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
                errors.append("information.confidence_user_has_fields must be a number between 0 and 1")
        
        if "can_request_from_patient" in information:
            if not isinstance(information["can_request_from_patient"], bool):
                errors.append("information.can_request_from_patient must be a boolean")
        
        if "sensitivity" in information:
            if not isinstance(information["sensitivity"], dict):
                errors.append("information.sensitivity must be a dictionary")
            else:
                sens = information["sensitivity"]
                if "phi_level" in sens and sens["phi_level"] not in self.VALID_PHI_LEVELS:
                    errors.append(f"information.sensitivity.phi_level must be one of {self.VALID_PHI_LEVELS}")
                if "pii_level" in sens and sens["pii_level"] not in self.VALID_PII_LEVELS:
                    errors.append(f"information.sensitivity.pii_level must be one of {self.VALID_PII_LEVELS}")
        
        return errors
    
    def _validate_policy(self, policy: Dict[str, Any]) -> List[str]:
        """Validate policy section."""
        errors = []
        if not isinstance(policy, dict):
            return ["policy must be a dictionary"]
        
        if "permissions_required" in policy:
            if not isinstance(policy["permissions_required"], list):
                errors.append("policy.permissions_required must be a list")
            elif not all(perm in self.VALID_PERMISSIONS for perm in policy["permissions_required"]):
                errors.append(f"policy.permissions_required must contain only values from {self.VALID_PERMISSIONS}")
        
        if "legal_template_required" in policy:
            if not isinstance(policy["legal_template_required"], bool):
                errors.append("policy.legal_template_required must be a boolean")
        
        if "approval_required" in policy:
            if not isinstance(policy["approval_required"], bool):
                errors.append("policy.approval_required must be a boolean")
        
        if "allowed_channels" in policy:
            if not isinstance(policy["allowed_channels"], list):
                errors.append("policy.allowed_channels must be a list")
            elif not all(channel in self.VALID_CHANNELS for channel in policy["allowed_channels"]):
                errors.append(f"policy.allowed_channels must contain only values from {self.VALID_CHANNELS}")
        
        return errors
    
    def _validate_temporal(self, temporal: Dict[str, Any]) -> List[str]:
        """Validate temporal section."""
        errors = []
        if not isinstance(temporal, dict):
            return ["temporal must be a dictionary"]
        
        if "expected_latency" in temporal:
            if temporal["expected_latency"] not in self.VALID_LATENCY_VALUES:
                errors.append(f"temporal.expected_latency must be one of {self.VALID_LATENCY_VALUES}")
        
        if "async_capable" in temporal:
            if not isinstance(temporal["async_capable"], bool):
                errors.append("temporal.async_capable must be a boolean")
        
        if "blocking_by_default" in temporal:
            if not isinstance(temporal["blocking_by_default"], bool):
                errors.append("temporal.blocking_by_default must be a boolean")
        
        if "deadline_sensitive" in temporal:
            if not isinstance(temporal["deadline_sensitive"], bool):
                errors.append("temporal.deadline_sensitive must be a boolean")
        
        return errors
    
    def _validate_escalation(self, escalation: Dict[str, Any]) -> List[str]:
        """Validate escalation section."""
        errors = []
        if not isinstance(escalation, dict):
            return ["escalation must be a dictionary"]
        
        if "escalate_on" in escalation:
            if not isinstance(escalation["escalate_on"], list):
                errors.append("escalation.escalate_on must be a list")
            elif not all(item in self.VALID_ESCALATE_ON for item in escalation["escalate_on"]):
                errors.append(f"escalation.escalate_on must contain only values from {self.VALID_ESCALATE_ON}")
        
        if "default_notify_frequency" in escalation:
            if escalation["default_notify_frequency"] not in self.VALID_NOTIFY_FREQUENCIES:
                errors.append(f"escalation.default_notify_frequency must be one of {self.VALID_NOTIFY_FREQUENCIES}")
        
        if "noise_budget" in escalation:
            if not isinstance(escalation["noise_budget"], dict):
                errors.append("escalation.noise_budget must be a dictionary")
            else:
                budget = escalation["noise_budget"]
                if "max_notifications_per_day" in budget:
                    if not isinstance(budget["max_notifications_per_day"], int) or budget["max_notifications_per_day"] < 0:
                        errors.append("escalation.noise_budget.max_notifications_per_day must be a non-negative integer")
                if "batching_allowed" in budget:
                    if not isinstance(budget["batching_allowed"], bool):
                        errors.append("escalation.noise_budget.batching_allowed must be a boolean")
        
        return errors
    
    def _validate_dependencies(self, dependencies: Dict[str, Any]) -> List[str]:
        """Validate dependencies section."""
        errors = []
        if not isinstance(dependencies, dict):
            return ["dependencies must be a dictionary"]
        
        if "depends_on_task_keys" in dependencies:
            if not isinstance(dependencies["depends_on_task_keys"], list):
                errors.append("dependencies.depends_on_task_keys must be a list")
            elif not all(isinstance(item, str) for item in dependencies["depends_on_task_keys"]):
                errors.append("dependencies.depends_on_task_keys must be a list of strings")
        
        if "blocks_task_keys" in dependencies:
            if not isinstance(dependencies["blocks_task_keys"], list):
                errors.append("dependencies.blocks_task_keys must be a list")
            elif not all(isinstance(item, str) for item in dependencies["blocks_task_keys"]):
                errors.append("dependencies.blocks_task_keys must be a list of strings")
        
        if "conditional_rules" in dependencies:
            if not isinstance(dependencies["conditional_rules"], list):
                errors.append("dependencies.conditional_rules must be a list")
            else:
                for rule in dependencies["conditional_rules"]:
                    if not isinstance(rule, dict):
                        errors.append("dependencies.conditional_rules must be a list of dictionaries")
                        break
        
        return errors
    
    def _validate_failure(self, failure: Dict[str, Any]) -> List[str]:
        """Validate failure section."""
        errors = []
        if not isinstance(failure, dict):
            return ["failure must be a dictionary"]
        
        if "retry_allowed" in failure:
            if not isinstance(failure["retry_allowed"], bool):
                errors.append("failure.retry_allowed must be a boolean")
        
        if "retry_limit" in failure:
            if not isinstance(failure["retry_limit"], int) or failure["retry_limit"] < 0:
                errors.append("failure.retry_limit must be a non-negative integer")
        
        if "retry_backoff" in failure:
            if failure["retry_backoff"] not in self.VALID_RETRY_BACKOFF:
                errors.append(f"failure.retry_backoff must be one of {self.VALID_RETRY_BACKOFF}")
        
        if "manual_override_allowed" in failure:
            if not isinstance(failure["manual_override_allowed"], bool):
                errors.append("failure.manual_override_allowed must be a boolean")
        
        return errors
    
    def _validate_ui(self, ui: Dict[str, Any]) -> List[str]:
        """Validate ui section."""
        errors = []
        if not isinstance(ui, dict):
            return ["ui must be a dictionary"]
        
        if "needs_user_input_by_default" in ui:
            if not isinstance(ui["needs_user_input_by_default"], bool):
                errors.append("ui.needs_user_input_by_default must be a boolean")
        
        if "input_type" in ui:
            if ui["input_type"] not in self.VALID_INPUT_TYPES:
                errors.append(f"ui.input_type must be one of {self.VALID_INPUT_TYPES}")
        
        return errors
    
    def _validate_governance(self, governance: Dict[str, Any]) -> List[str]:
        """Validate governance section."""
        errors = []
        if not isinstance(governance, dict):
            return ["governance must be a dictionary"]
        
        if "version" in governance:
            if not isinstance(governance["version"], int) or governance["version"] < 1:
                errors.append("governance.version must be a positive integer")
        
        if "status" in governance:
            if governance["status"] not in self.VALID_STATUSES:
                errors.append(f"governance.status must be one of {self.VALID_STATUSES}")
        
        return errors


# Singleton instance
task_schema_validator = TaskSchemaValidator()







