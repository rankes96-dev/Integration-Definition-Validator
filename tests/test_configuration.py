from __future__ import annotations

import asyncio
import json
import logging

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from starlette.types import Message, Scope

from app.core.config import Settings, get_settings
from app.core.logging import JsonFormatter, configure_logging
from app.main import create_app


def test_cors_can_be_enabled_for_explicit_origins() -> None:
    application = create_app(Settings(cors_allowed_origins=("https://portal.example.com",)))

    with TestClient(application) as client:
        response = client.options(
            "/api/v1/validate",
            headers={
                "Origin": "https://portal.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ("https://portal.example.com")


def test_cors_origins_are_read_from_comma_separated_environment(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        " https://one.example ,https://two.example, ",
    )
    get_settings.cache_clear()
    try:
        assert get_settings().cors_allowed_origins == (
            "https://one.example",
            "https://two.example",
        )
    finally:
        get_settings.cache_clear()


def test_request_body_limit_is_configurable() -> None:
    application = create_app(Settings(max_request_body_bytes=32))

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/validate",
            content=b"x" * 33,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["message"] == "Request body must not exceed 32 bytes"


def test_streamed_request_without_content_length_is_limited() -> None:
    application = create_app(Settings(max_request_body_bytes=32))
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/validate",
        "raw_path": b"/api/v1/validate",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    incoming = iter(
        [
            {"type": "http.request", "body": b"x" * 20, "more_body": True},
            {"type": "http.request", "body": b"x" * 13, "more_body": False},
        ]
    )
    sent: list[Message] = []

    async def receive() -> Message:
        return next(incoming)  # type: ignore[return-value]

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(application(scope, receive, send))

    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"") for message in sent if message["type"] == "http.response.body"
    )
    assert start["status"] == 413
    assert json.loads(body)["error"] == "request_body_too_large"


def test_json_formatter_emits_structured_metadata() -> None:
    record = logging.LogRecord(
        name="app.validation",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Integration validation completed",
        args=(),
        exc_info=None,
    )
    record.event = "integration_validation_completed"
    record.score = 100

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "info"
    assert payload["logger"] == "app.validation"
    assert payload["message"] == "Integration validation completed"
    assert payload["event"] == "integration_validation_completed"
    assert payload["score"] == 100
    assert "timestamp" in payload


def test_configure_logging_structures_uvicorn_logs_and_disables_access(
    monkeypatch: MonkeyPatch,
) -> None:
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")

    for logger in (uvicorn_logger, uvicorn_error_logger, uvicorn_access_logger):
        monkeypatch.setattr(logger, "handlers", [logging.NullHandler()])
        monkeypatch.setattr(logger, "disabled", False)
        monkeypatch.setattr(logger, "propagate", False)

    configure_logging()

    assert len(uvicorn_logger.handlers) == 1
    assert isinstance(uvicorn_logger.handlers[0].formatter, JsonFormatter)
    assert uvicorn_logger.propagate is False

    assert uvicorn_error_logger.handlers == []
    assert uvicorn_error_logger.propagate is True
    assert uvicorn_error_logger.parent is uvicorn_logger

    assert uvicorn_access_logger.handlers == []
    assert uvicorn_access_logger.propagate is False
    assert uvicorn_access_logger.disabled is True
