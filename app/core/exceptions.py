"""Public exceptions expose safe messages, never raw provider payloads."""


class JobPilotError(Exception):
    """Base application error."""


class ConfigurationError(JobPilotError):
    """Missing or invalid runtime configuration."""


class ModelCallError(JobPilotError):
    """Provider request failed; output is intentionally redacted."""


class StructuredOutputError(JobPilotError):
    """Model response does not satisfy the requested contract."""
