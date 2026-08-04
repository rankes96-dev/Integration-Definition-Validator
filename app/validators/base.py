"""Shared interface and helpers for semantic validation rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import ClassVar

from app.models import Category, Finding, IntegrationDefinition, Severity

_MAX_FINDING_PATH_LENGTH = 500
_MAX_FINDING_TEXT_LENGTH = 1_000


def _bounded_text(value: str, max_length: int) -> str:
    """Bound user-influenced finding content to the public response schema."""

    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


class ValidationRule(ABC):
    """A stateless, independently executable semantic validation rule."""

    rule_id: ClassVar[str]
    category: ClassVar[Category]
    default_severity: ClassVar[Severity]
    title: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        """Evaluate *definition* and return findings produced by this rule."""

    def finding(self, *, path: str, message: str, recommendation: str) -> Finding:
        """Build a finding populated with this rule's fixed metadata."""
        return Finding(
            rule_id=self.rule_id,
            severity=self.default_severity,
            category=self.category,
            path=_bounded_text(path, _MAX_FINDING_PATH_LENGTH),
            message=_bounded_text(message, _MAX_FINDING_TEXT_LENGTH),
            recommendation=_bounded_text(recommendation, _MAX_FINDING_TEXT_LENGTH),
        )


def enum_value(value: object) -> object:
    """Return an enum's serialized value while leaving other objects unchanged."""
    if isinstance(value, Enum):
        return value.value
    return value


def is_blank(value: object) -> bool:
    """Return whether a nullable text value is absent or only whitespace."""
    return value is None or (isinstance(value, str) and not value.strip())
