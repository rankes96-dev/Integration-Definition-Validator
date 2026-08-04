"""Models describing validation rules and their findings."""

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints

from app.models._base import APIModel


class Severity(StrEnum):
    """Impact level assigned to a validation finding."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(StrEnum):
    """Functional area covered by a validation rule."""

    SCHEMA = "schema"
    SECURITY = "security"
    RELIABILITY = "reliability"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    API_DESIGN = "api_design"


RuleId = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        min_length=5,
        max_length=32,
        pattern=r"^[A-Z]+-[0-9]{3}$",
    ),
]
FindingPath = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500),
]
FindingText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=1_000),
]


class Finding(APIModel):
    """A single actionable issue discovered by a validation rule."""

    rule_id: RuleId = Field(
        description="Stable identifier of the rule that produced the finding.",
        examples=["SEC-002"],
    )
    severity: Severity = Field(
        description="Impact level of the finding.",
        examples=[Severity.ERROR.value],
    )
    category: Category = Field(
        description="Functional category of the validation rule.",
        examples=[Category.SECURITY.value],
    )
    path: FindingPath = Field(
        description="Dot-and-index path to the affected field.",
        examples=["authentication.credential_references[0]"],
    )
    message: FindingText = Field(
        description="Clear explanation of the detected issue.",
        examples=["A credential value appears to be embedded directly."],
    )
    recommendation: FindingText = Field(
        description="Action the caller can take to resolve the issue.",
        examples=["Use an environment variable or secret reference name instead."],
    )


class RuleMetadata(APIModel):
    """Public documentation for an available validation rule."""

    id: RuleId = Field(
        description="Stable validation rule identifier.",
        examples=["SEC-001"],
    )
    category: Category = Field(
        description="Functional category evaluated by the rule.",
        examples=[Category.SECURITY.value],
    )
    severity: Severity = Field(
        description="Default impact level emitted by the rule.",
        examples=[Severity.ERROR.value],
    )
    title: Annotated[
        str,
        StringConstraints(
            strict=True,
            strip_whitespace=True,
            min_length=1,
            max_length=200,
        ),
    ] = Field(
        description="Short human-readable rule title.",
        examples=["HTTPS is required"],
    )
    description: FindingText = Field(
        description="Explanation of what the rule validates.",
        examples=["External API URLs must use HTTPS."],
    )
