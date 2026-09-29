"""Structured JSON logging configuration with automated PII redaction.

Rule: Candidate names, emails, raw search queries, and notes must never be logged.
Only IDs, hashes, counts, and metadata are permitted in application logs (SYSTEM_DESIGN §16).
"""

import json
import logging
from typing import Any

STANDARD_LOG_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)

DENYLIST_KEYS = frozenset({"full_name", "name", "email", "q", "query", "note"})


class PIIRedactionFilter(logging.Filter):
    """Logging filter that removes PII keys from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record by deleting denylisted PII extra attributes from record."""
        for key in DENYLIST_KEYS:
            if key not in STANDARD_LOG_RECORD_ATTRS and hasattr(record, key):
                delattr(record, key)
        return True


class JSONFormatter(logging.Formatter):
    """Formatter that outputs structured log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as a single JSON line."""
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        standard_attrs = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
        }

        for key, val in record.__dict__.items():
            if key not in standard_attrs and key not in DENYLIST_KEYS:
                log_obj[key] = val

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with JSONFormatter and PIIRedactionFilter."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(PIIRedactionFilter())

    root_logger.addHandler(handler)
