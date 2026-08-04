"""Response models returned by validation API endpoints."""

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictBool, StringConstraints

from app.models._base import APIModel
from app.models.finding import Finding, RuleMetadata


class Grade(StrEnum):
    """Letter grade derived from a validation score."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


Count = Annotated[int, Field(strict=True, ge=0)]
Score = Annotated[int, Field(strict=True, ge=0, le=100)]


class ValidationSummary(APIModel):
    """Finding counts grouped by severity."""

    critical: Count = Field(
        default=0,
        description="Number of critical findings.",
        examples=[0],
    )
    errors: Count = Field(
        default=0,
        description="Number of error findings.",
        examples=[1],
    )
    warnings: Count = Field(
        default=0,
        description="Number of warning findings.",
        examples=[2],
    )
    info: Count = Field(
        default=0,
        description="Number of informational findings.",
        examples=[0],
    )


class ValidationResponse(APIModel):
    """Complete result of statically validating an integration definition."""

    validation_id: UUID = Field(
        description="Unique identifier generated for this validation request.",
        examples=["36e83a67-c988-4e9a-b0da-a44d71e338ad"],
    )
    validated_at: AwareDatetime = Field(
        description="Timezone-aware timestamp at which validation completed.",
        examples=["2026-08-04T12:00:00Z"],
    )
    integration_name: Annotated[
        str,
        StringConstraints(
            strict=True,
            strip_whitespace=True,
            min_length=3,
            max_length=100,
        ),
    ] = Field(
        description="Name of the integration that was validated.",
        examples=["Monday Integration"],
    )
    valid: StrictBool = Field(
        description="True when no critical or error findings were produced.",
        examples=[False],
    )
    score: Score = Field(
        description="Quality score from 0 to 100.",
        examples=[75],
    )
    grade: Grade = Field(
        description="Letter grade derived from the score.",
        examples=[Grade.C.value],
    )
    summary: ValidationSummary = Field(
        description="Counts of findings grouped by severity.",
        examples=[{"critical": 0, "errors": 1, "warnings": 2, "info": 0}],
    )
    findings: list[Finding] = Field(
        description="Ordered validation findings with remediation guidance.",
        examples=[
            [
                {
                    "rule_id": "SEC-001",
                    "severity": "error",
                    "category": "security",
                    "path": "base_url",
                    "message": "The external API URL does not use HTTPS.",
                    "recommendation": "Use an HTTPS URL for external APIs.",
                }
            ]
        ],
    )


class RulesResponse(APIModel):
    """Catalog of validation rules exposed by the service."""

    rules: list[RuleMetadata] = Field(
        description="Metadata for every validation rule available in the service.",
        examples=[
            [
                {
                    "id": "SEC-001",
                    "category": "security",
                    "severity": "error",
                    "title": "HTTPS required",
                    "description": "External API URLs must use HTTPS.",
                }
            ]
        ],
    )
