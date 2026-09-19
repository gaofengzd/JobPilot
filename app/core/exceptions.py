"""Public exceptions expose safe messages, never raw provider payloads."""


class JobPilotError(Exception):
    """Base application error."""


class ConfigurationError(JobPilotError):
    """Missing or invalid runtime configuration."""


class ModelCallError(JobPilotError):
    """Provider request failed; output is intentionally redacted."""


class StructuredOutputError(JobPilotError):
    """Model response does not satisfy the requested contract."""


class ResumeReadError(JobPilotError):
    """Resume file cannot be safely read as supported text."""


class ResumeGroundingError(JobPilotError):
    """Extracted candidate facts cannot be grounded in the resume."""
