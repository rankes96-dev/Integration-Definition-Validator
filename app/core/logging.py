"""Structured JSON logging without request-body or credential data."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_STANDARD_LOG_RECORD_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "color_message",
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
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    """Render log records as one compact JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_FIELDS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    """Configure application and server logs for safe structured output."""

    formatter = JsonFormatter()

    app_logger = logging.getLogger("app")
    if not any(
        getattr(handler, "_integration_validator", False) for handler in app_logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler._integration_validator = True  # type: ignore[attr-defined]
        app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    uvicorn_logger = logging.getLogger("uvicorn")
    if not any(
        getattr(handler, "_integration_validator", False) for handler in uvicorn_logger.handlers
    ):
        uvicorn_logger.handlers.clear()
        server_handler = logging.StreamHandler()
        server_handler.setFormatter(formatter)
        server_handler._integration_validator = True  # type: ignore[attr-defined]
        uvicorn_logger.addHandler(server_handler)
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_logger.propagate = False

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.propagate = True

    # Access records include raw query strings, which may contain credentials.
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.propagate = False
    uvicorn_access_logger.disabled = True
