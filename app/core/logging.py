"""Allowlisted JSON events; do not log prompts, model text or exception bodies."""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

EVENT_FIELDS = (
    "request_id",
    "job_index",
    "node",
    "status",
    "duration_ms",
    "attempt",
    "error_type",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "model",
    "model_url",
    "input_chars",
    "input_sha256",
    "input_preview",
    "output_chars",
    "output_sha256",
    "output_preview",
    "grounding_issue",
    "unsupported_count",
    "unsupported_fields",
    "unsupported_chars",
    "unsupported_sha256",
    "unsupported_preview",
)


class JsonFormatter(logging.Formatter):
    def __init__(self, timezone: str = "Asia/Shanghai") -> None:
        super().__init__()
        try:
            self._timezone = ZoneInfo(timezone)
        except KeyError:
            self._timezone = ZoneInfo("Asia/Shanghai")

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(self._timezone).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in EVENT_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    level: str = "INFO",
    stream: TextIO | None = None,
    log_dir: Path | None = None,
) -> logging.Logger:
    logger = logging.getLogger("jobpilot")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    timezone = os.getenv("LOG_TIMEZONE", "Asia/Shanghai")
    handler.setFormatter(JsonFormatter(timezone))
    logger.addHandler(handler)
    target_dir = log_dir or Path(__file__).resolve().parents[2] / "log"
    target_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(target_dir / "jobpilot.log", encoding="utf-8")
    file_handler.setFormatter(JsonFormatter(timezone))
    logger.addHandler(file_handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def content_fields(
    value: object,
    *,
    prefix: str = "input",
    capture: bool | None = None,
) -> dict[str, object]:
    """Return bounded, non-secret content diagnostics for local debugging."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    result: dict[str, object] = {
        f"{prefix}_chars": len(text),
        f"{prefix}_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    enabled = (
        capture
        if capture is not None
        else os.getenv("LOG_CAPTURE_CONTENT", "false").lower() == "true"
    )
    if enabled:
        result[f"{prefix}_preview"] = text[:2000]
    return result


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: object,
) -> None:
    # event is a developer-defined constant, never user-provided text.
    logger.log(
        level,
        event,
        extra={key: value for key, value in fields.items() if key in EVENT_FIELDS},
    )
