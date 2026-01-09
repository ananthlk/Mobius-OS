"""
Eligibility Agent V2 - Exceptions
"""


class EligibilityAgentError(Exception):
    """Base exception for eligibility agent errors"""
    pass


class LLMResponseValidationError(EligibilityAgentError):
    """Raised when LLM response doesn't match expected schema"""
    pass


class CaseNotFoundError(EligibilityAgentError):
    """Raised when a case is not found"""
    pass


class InvalidStateTransitionError(EligibilityAgentError):
    """Raised when an invalid state transition is attempted"""
    pass
