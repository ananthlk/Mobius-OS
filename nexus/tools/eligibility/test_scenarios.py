"""
Test Scenarios Configuration
Maps specific MRNs to test scenarios for eligibility failures and missing data.

This ensures deterministic behavior: the same MRN will always return the same test scenario
regardless of whether accessed from Spectacles, Portal, or any other interface.
"""
from typing import Dict, Any, Optional

# Test scenario configurations
# Format: MRN -> scenario configuration
TEST_SCENARIOS: Dict[str, Dict[str, Any]] = {
    # ========================================================================
    # ELIGIBILITY FAILURE SCENARIOS
    # ========================================================================
    
    # MRNs that should have NO eligibility (no active window)
    "MRN200": {
        "eligibility_result": "NO_ACTIVE_WINDOW",  # No active coverage
        "demographics": "FULL",  # Has demographics
        "insurance": "FULL",  # Has insurance
        "visits": "FULL"  # Has visits
    },
    "MRN201": {
        "eligibility_result": "NO_ACTIVE_WINDOW",
        "demographics": "FULL",
        "insurance": "FULL",
        "visits": "NONE"  # No visits
    },
    
    # MRNs with expired coverage (past end date)
    "MRN202": {
        "eligibility_result": "EXPIRED",  # Coverage expired
        "demographics": "FULL",
        "insurance": "FULL",
        "visits": "FULL"
    },
    
    # MRNs with future coverage (not yet effective)
    "MRN203": {
        "eligibility_result": "FUTURE",  # Coverage starts in future
        "demographics": "FULL",
        "insurance": "FULL",
        "visits": "FULL"
    },
    
    # ========================================================================
    # MISSING DATA SCENARIOS
    # ========================================================================
    
    # MRNs with missing demographics
    "MRN204": {
        "eligibility_result": "ACTIVE",
        "demographics": "NONE",  # Missing demographics
        "insurance": "FULL",
        "visits": "FULL"
    },
    "MRN205": {
        "eligibility_result": "ACTIVE",
        "demographics": "PARTIAL",  # Partial demographics (missing DOB)
        "insurance": "FULL",
        "visits": "FULL"
    },
    "MRN206": {
        "eligibility_result": "ACTIVE",
        "demographics": "PARTIAL_NAME",  # Missing first/last name
        "insurance": "FULL",
        "visits": "FULL"
    },
    
    # MRNs with missing insurance
    "MRN207": {
        "eligibility_result": "NO_ACTIVE_WINDOW",  # Can't check without insurance
        "demographics": "FULL",
        "insurance": "NONE",  # Missing insurance
        "visits": "FULL"
    },
    "MRN208": {
        "eligibility_result": "ACTIVE",
        "demographics": "FULL",
        "insurance": "PARTIAL",  # Partial insurance (missing plan_name)
        "visits": "FULL"
    },
    "MRN209": {
        "eligibility_result": "ACTIVE",
        "demographics": "FULL",
        "insurance": "PARTIAL_PAYER",  # Missing payer_name
        "visits": "FULL"
    },
    
    # MRNs with no visits
    "MRN210": {
        "eligibility_result": "ACTIVE",
        "demographics": "FULL",
        "insurance": "FULL",
        "visits": "NONE"  # No visits
    },
    
    # ========================================================================
    # COMBINED FAILURE SCENARIOS
    # ========================================================================
    
    # Multiple failures: NO eligibility + missing data
    "MRN211": {
        "eligibility_result": "NO_ACTIVE_WINDOW",
        "demographics": "PARTIAL",
        "insurance": "PARTIAL",
        "visits": "NONE"
    },
    
    # NO eligibility + missing demographics
    "MRN212": {
        "eligibility_result": "NO_ACTIVE_WINDOW",
        "demographics": "NONE",
        "insurance": "FULL",
        "visits": "FULL"
    },
    
    # NO eligibility + missing insurance
    "MRN213": {
        "eligibility_result": "NO_ACTIVE_WINDOW",
        "demographics": "FULL",
        "insurance": "NONE",
        "visits": "FULL"
    },
    
    # Expired coverage + no visits
    "MRN214": {
        "eligibility_result": "EXPIRED",
        "demographics": "FULL",
        "insurance": "FULL",
        "visits": "NONE"
    },
    
    # Future coverage + partial data
    "MRN215": {
        "eligibility_result": "FUTURE",
        "demographics": "PARTIAL",
        "insurance": "PARTIAL",
        "visits": "FULL"
    },
}


def get_test_scenario(patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Get test scenario configuration for a patient_id.
    
    Args:
        patient_id: Patient ID (e.g., "MRN200", "mrn200", "MRN200")
    
    Returns:
        Test scenario configuration dict or None if not a test scenario
    """
    # Normalize patient_id to uppercase for lookup
    normalized_id = patient_id.upper().strip()
    return TEST_SCENARIOS.get(normalized_id)


def is_test_scenario(patient_id: str) -> bool:
    """
    Check if a patient_id is a test scenario.
    
    Args:
        patient_id: Patient ID to check
    
    Returns:
        True if patient_id is a test scenario, False otherwise
    """
    return get_test_scenario(patient_id) is not None


def list_test_scenarios() -> Dict[str, Dict[str, Any]]:
    """
    List all available test scenarios.
    
    Returns:
        Dictionary of all test scenarios
    """
    return TEST_SCENARIOS.copy()
