"""FastAPI application factory and production entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.health import router as health_router
from app.api.rules import router as rules_router
from app.api.validation import router as validation_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestBodyLimitMiddleware
from app.models import (
    ErrorDetail,
    InternalServerErrorResponse,
    SchemaValidationErrorResponse,
)

logger = logging.getLogger("app.api")
_MAX_ERROR_TEXT_LENGTH = 1_000


def _bounded_error_text(value: str) -> str:
    if len(value) <= _MAX_ERROR_TEXT_LENGTH:
        return value
    return f"{value[: _MAX_ERROR_TEXT_LENGTH - 3]}..."


def _validation_error_path(location: tuple[int | str, ...]) -> str:
    source_prefixes = {"body", "query", "path", "header", "cookie"}
    normalized_location = location[1:] if location and location[0] in source_prefixes else location
    parts = [str(part) for part in normalized_location]
    return _bounded_error_text(".".join(parts) or "request")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured, stateless application instance."""

    resolved_settings = settings or get_settings()
    configure_logging()
    application = FastAPI(
        title="Integration Definition Validator",
        summary="Static validation for API integration definitions",
        description=(
            "Checks integration definitions for schema, API design, security, reliability, "
            "testing, and documentation issues without making outbound requests."
        ),
        version=resolved_settings.service_version,
        contact={"name": "Integration Platform Team"},
        license_info={"name": "MIT"},
    )
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=resolved_settings.max_request_body_bytes,
    )
    if resolved_settings.cors_allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.cors_allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    @application.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @application.exception_handler(RequestValidationError)
    async def schema_validation_exception_handler(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        del request
        details = [
            ErrorDetail(
                path=_validation_error_path(tuple(error["loc"])),
                message=_bounded_error_text(error["msg"]),
            )
            for error in exception.errors()
        ]
        payload = SchemaValidationErrorResponse(details=details)
        return JSONResponse(
            status_code=422,
            content=payload.model_dump(mode="json"),
        )

    @application.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exception: Exception) -> JSONResponse:
        logger.error(
            "Unexpected validation request failure",
            extra={
                "event": "validation_request_failed",
                "path": request.url.path,
                "exception_type": type(exception).__name__,
            },
        )
        payload = InternalServerErrorResponse()
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))

    application.include_router(health_router)
    application.include_router(rules_router)
    application.include_router(validation_router)
    return application


app = create_app()
