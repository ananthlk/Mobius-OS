"""
Completion Checker

Determines if a case is complete.
"""
import logging
from nexus.agents.eligibility_v2.models import (
    CaseState, CompletionStatus, CompletionStatusModel, ProductType, ContractStatus, EventTense
)

logger = logging.getLogger("nexus.eligibility_v2.completion_checker")


class CompletionChecker:
    """Checks if case is complete"""
    
    def check_completion(self, case_state: CaseState) -> CompletionStatus:
        """Check if case is complete"""
        missing_fields = []
        
        # Check for UNKNOWN values
        if case_state.health_plan.product_type == ProductType.UNKNOWN:
            missing_fields.append("health_plan.product_type")
        
        if case_state.health_plan.contract_status == ContractStatus.UNKNOWN:
            missing_fields.append("health_plan.contract_status")
        
        if case_state.timing.event_tense == EventTense.UNKNOWN and not case_state.timing.dos_date:
            missing_fields.append("timing.dos_date")
        
        if not missing_fields:
            status = CompletionStatus.COMPLETE
        else:
            status = CompletionStatus.INCOMPLETE
        
        from nexus.agents.eligibility_v2.models import CompletionStatusModel
        return CompletionStatusModel(
            status=status,
            missing_fields=missing_fields
        )
