"""Allowlisted JSON events; do not log prompts, model text or exception bodies."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import TextIO

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
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in EVENT_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> logging.Logger:
    logger = logging.getLogger("jobpilot")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    # event is a developer-defined constant, never user-provided text.
    logger.info(event, extra={key: value for key, value in fields.items() if key in EVENT_FIELDS})
