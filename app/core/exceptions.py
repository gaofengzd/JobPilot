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


class JobGroundingError(JobPilotError):
    """Extracted job facts cannot be grounded in the job description."""


class MatchCalculationError(JobPilotError):
    """Deterministic matching or embedding validation failed."""


class GapAnalysisError(JobPilotError):
    """A skill gap cannot be linked to its job and JD evidence."""


class BatchAnalysisError(JobPilotError):
    """Batch inputs or deterministic statistics are inconsistent."""


class RetrievalError(JobPilotError):
    """Knowledge loading, indexing, or retrieval failed safely."""


class ToolArgumentError(JobPilotError):
    """A model tool request does not match the graph-approved inputs."""
