"""Request models for integration definitions."""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import (
    AnyHttpUrl,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
)

from app.models._base import APIModel


class AuthType(StrEnum):
    """Authentication mechanisms supported by an integration."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC = "basic"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"
    OAUTH2_AUTHORIZATION_CODE = "oauth2_authorization_code"


class ApiKeyLocation(StrEnum):
    """Locations in which an API key may be sent."""

    HEADER = "header"
    QUERY = "query"


class HttpMethod(StrEnum):
    """HTTP methods supported by a command."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class DataType(StrEnum):
    """Data types available for command parameters."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ParameterLocation(StrEnum):
    """Locations in which command parameters may appear."""

    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"


class BackoffStrategy(StrEnum):
    """Backoff algorithms supported by retry policies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class TestCaseType(StrEnum):
    """Behavioral scenarios that can be documented for a command."""

    SUCCESS = "success"
    AUTH_FAILURE = "auth_failure"
    VALIDATION_FAILURE = "validation_failure"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"


IntegrationName = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=3, max_length=100),
]
ShortText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100),
]
Description = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, max_length=500),
]
Reference = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=255),
]
CommandName = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]
CommandPath = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        min_length=1,
        max_length=2_048,
    ),
]
HttpStatusCode = Annotated[int, Field(strict=True, ge=100, le=599)]


class AuthenticationDefinition(APIModel):
    """Authentication settings used by the external API."""

    type: AuthType = Field(
        description="Authentication mechanism used by the integration.",
        examples=[AuthType.OAUTH2_CLIENT_CREDENTIALS.value],
    )
    credential_references: list[Reference] = Field(
        default_factory=list,
        description=(
            "Names of environment variables or secret references; never raw credential values."
        ),
        examples=[["MONDAY_CLIENT_ID", "MONDAY_CLIENT_SECRET"]],
    )
    authorization_url: AnyHttpUrl | None = Field(
        default=None,
        description="OAuth authorization endpoint, when required by the auth type.",
        examples=["https://auth.example.com/oauth/authorize"],
    )
    token_url: AnyHttpUrl | None = Field(
        default=None,
        description="OAuth token endpoint, when required by the auth type.",
        examples=["https://auth.example.com/oauth/token"],
    )
    scopes: list[Reference] = Field(
        default_factory=list,
        description="OAuth scopes requested by the integration.",
        examples=[["boards:read", "boards:write"]],
    )
    api_key_name: ShortText | None = Field(
        default=None,
        description="Header or query-parameter name used for API-key authentication.",
        examples=["X-API-Key"],
    )
    api_key_location: ApiKeyLocation | None = Field(
        default=None,
        description="Location in which an API key is sent.",
        examples=[ApiKeyLocation.HEADER.value],
    )


class ParameterDefinition(APIModel):
    """Input or output field exposed by a command."""

    name: ShortText = Field(
        description="Parameter name as used by the external API.",
        examples=["board_id"],
    )
    type: DataType = Field(
        description="JSON-compatible data type of the parameter.",
        examples=[DataType.STRING.value],
    )
    location: ParameterLocation = Field(
        description="Request or response location of the parameter.",
        examples=[ParameterLocation.BODY.value],
    )
    required: StrictBool = Field(
        description="Whether the parameter must be present.",
        examples=[True],
    )
    description: Description | None = Field(
        default=None,
        description="Human-readable explanation of the parameter.",
        examples=["The target board identifier."],
    )
    sensitive: StrictBool = Field(
        default=False,
        description="Whether values for this parameter contain sensitive data.",
        examples=[False],
    )
    example: Any | None = Field(
        default=None,
        description="Example parameter value for generated API documentation.",
        examples=["123456"],
    )


class RetryPolicy(APIModel):
    """Automatic retry behavior for transient upstream failures."""

    enabled: StrictBool = Field(
        default=True,
        description="Whether automatic retries are enabled.",
        examples=[True],
    )
    max_attempts: Annotated[int, Field(strict=True, ge=1, le=5)] = Field(
        default=3,
        description="Maximum number of attempts, including the initial request.",
        examples=[3],
    )
    backoff_strategy: BackoffStrategy = Field(
        default=BackoffStrategy.EXPONENTIAL,
        description="Delay strategy applied between retry attempts.",
        examples=[BackoffStrategy.EXPONENTIAL.value],
    )
    retry_on_status_codes: list[HttpStatusCode] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP response status codes that trigger an automatic retry.",
        examples=[[429, 500, 502, 503, 504]],
    )


class TestCaseDefinition(APIModel):
    """Static test scenario documented for a command."""

    name: Annotated[
        str,
        StringConstraints(
            strict=True,
            strip_whitespace=True,
            min_length=1,
            max_length=200,
        ),
    ] = Field(
        description="Human-readable name of the test scenario.",
        examples=["authentication failure"],
    )
    type: TestCaseType = Field(
        description="Behavioral scenario covered by the test case.",
        examples=[TestCaseType.AUTH_FAILURE.value],
    )
    expected_status_code: HttpStatusCode | None = Field(
        default=None,
        description="Expected HTTP response status code, when applicable.",
        examples=[401],
    )


class CommandDefinition(APIModel):
    """Operation exposed by the integration."""

    name: CommandName = Field(
        description=("Command name; semantic validation checks uniqueness and snake_case."),
        examples=["get_board_items"],
    )
    description: Description | None = Field(
        default=None,
        description="Human-readable explanation of the command.",
        examples=["Returns items from a board."],
    )
    method: HttpMethod = Field(
        description="HTTP method used by the external API operation.",
        examples=[HttpMethod.POST.value],
    )
    path: CommandPath = Field(
        description=(
            "External API path; semantic validation checks that it begins with a forward slash."
        ),
        examples=["/v2"],
    )
    inputs: list[ParameterDefinition] = Field(
        default_factory=list,
        max_length=100,
        description="Input parameters accepted by the command (maximum 100).",
        examples=[
            [
                {
                    "name": "board_id",
                    "type": "string",
                    "location": "body",
                    "required": True,
                }
            ]
        ],
    )
    outputs: list[ParameterDefinition] = Field(
        default_factory=list,
        max_length=100,
        description="Output fields returned by the command (maximum 100).",
        examples=[
            [
                {
                    "name": "items",
                    "type": "array",
                    "location": "body",
                    "required": True,
                }
            ]
        ],
    )
    expected_status_codes: list[HttpStatusCode] = Field(
        min_length=1,
        description="Expected HTTP status codes; at least one code is required.",
        examples=[[200]],
    )
    idempotency_key_supported: StrictBool = Field(
        default=False,
        description="Whether the operation supports idempotency protection.",
        examples=[False],
    )
    test_cases: list[TestCaseDefinition] = Field(
        default_factory=list,
        max_length=50,
        description="Static test scenarios for the command (maximum 50).",
        examples=[[{"name": "successful request", "type": "success", "expected_status_code": 200}]],
    )


class IntegrationDefinition(APIModel):
    """Complete static definition submitted to the validation service."""

    name: IntegrationName = Field(
        description="Display name of the integration (3 to 100 characters).",
        examples=["Monday Board Integration"],
    )
    description: Description | None = Field(
        default=None,
        description="Human-readable purpose and capabilities of the integration.",
        examples=["Reads and creates items in monday.com boards."],
    )
    version: Annotated[
        str,
        StringConstraints(
            strict=True,
            strip_whitespace=True,
            min_length=1,
            max_length=64,
        ),
    ] = Field(
        description="Integration version; semantic versioning is recommended.",
        examples=["1.0.0"],
    )
    base_url: AnyHttpUrl = Field(
        description="HTTP(S) base URL of the external API.",
        examples=["https://api.monday.com/v2"],
    )
    owner: ShortText | None = Field(
        default=None,
        description="Team or individual responsible for the integration.",
        examples=["integration-team"],
    )
    authentication: AuthenticationDefinition = Field(
        description="Authentication settings for the external API.",
        examples=[
            {
                "type": "bearer_token",
                "credential_references": ["API_BEARER_TOKEN"],
            }
        ],
    )
    timeout_seconds: Annotated[int, Field(strict=True, ge=1, le=60)] = Field(
        default=15,
        description="Per-request timeout in seconds (1 to 60).",
        examples=[15],
    )
    retry_policy: RetryPolicy | None = Field(
        default=None,
        description="Optional automatic retry policy for transient failures.",
        examples=[
            {
                "enabled": True,
                "max_attempts": 3,
                "backoff_strategy": "exponential",
                "retry_on_status_codes": [429, 500, 502, 503, 504],
            }
        ],
    )
    commands: list[CommandDefinition] = Field(
        min_length=1,
        max_length=100,
        description="Commands exposed by the integration (1 to 100).",
        examples=[
            [
                {
                    "name": "health_check",
                    "method": "GET",
                    "path": "/health",
                    "expected_status_codes": [200],
                }
            ]
        ],
    )
    tags: list[ShortText] = Field(
        default_factory=list,
        description="Unique searchable labels for the integration.",
        examples=[["monday", "project-management"]],
    )

    @field_validator("tags")
    @classmethod
    def tags_must_be_unique(cls, tags: list[str]) -> list[str]:
        """Reject duplicate tags while preserving their submitted order."""

        if len(tags) != len(set(tags)):
            raise ValueError("tags must not contain duplicates")
        return tags
