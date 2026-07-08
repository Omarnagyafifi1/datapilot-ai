from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

# Per-request context for injecting request_id into log records
_request_id: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(rid: str) -> None:
    _request_id.set(rid)


def get_request_id() -> str:
    return _request_id.get()


def generate_request_id() -> str:
    return uuid.uuid4().hex[:12]


class StructuredFormatter(logging.Formatter):
    """JSON formatter that includes request_id and structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        if hasattr(record, "extra_fields"):
            log_entry["extra"] = record.extra_fields
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


def _setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


_setup_logging()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_with_extra(logger: logging.Logger, level: str, message: str, **extra: Any) -> None:
    """Log a message with extra structured fields."""
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper(), logging.INFO),
        "", 0, message, (), None,
    )
    record.extra_fields = extra
    logger.handleRecord(record)
