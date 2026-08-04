"""Structured API error response models."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.models._base import APIModel

ErrorText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=1_000),
]


class ErrorDetail(APIModel):
    """Location and explanation of one structural schema error."""

    path: ErrorText = Field(
        description="Dot-separated path to the invalid request field",
        examples=["commands.0.method"],
    )
    message: ErrorText = Field(
        description="Human-readable schema validation message",
        examples=["Input should be GET, POST, PUT, PATCH or DELETE"],
    )


class SchemaValidationErrorResponse(APIModel):
    """Response returned when the request does not match the Pydantic schema."""

    error: Literal["schema_validation_failed"] = Field(
        default="schema_validation_failed",
        description="Stable machine-readable error code",
        examples=["schema_validation_failed"],
    )
    message: ErrorText = Field(
        default="The integration definition does not match the required schema",
        description="Human-readable error summary",
        examples=["The integration definition does not match the required schema"],
    )
    details: list[ErrorDetail] = Field(
        description="All structural validation failures",
        examples=[
            [
                {
                    "path": "commands.0.method",
                    "message": "Input should be GET, POST, PUT, PATCH or DELETE",
                }
            ]
        ],
    )


class InternalServerErrorResponse(APIModel):
    """Sanitized response for an unexpected request failure."""

    error: Literal["internal_server_error"] = Field(
        default="internal_server_error",
        description="Stable machine-readable error code",
        examples=["internal_server_error"],
    )
    message: ErrorText = Field(
        default="The validation request could not be completed",
        description="Sanitized human-readable error summary",
        examples=["The validation request could not be completed"],
    )


class RequestBodyTooLargeResponse(APIModel):
    """Response returned when the request exceeds the configured byte limit."""

    error: Literal["request_body_too_large"] = Field(
        default="request_body_too_large",
        description="Stable machine-readable error code",
        examples=["request_body_too_large"],
    )
    message: ErrorText = Field(
        description="Configured request body size limit",
        examples=["Request body must not exceed 262144 bytes"],
    )
