"""Finding scoring and summary calculations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import ClassVar

from app.models import Finding, Severity, ValidationSummary


class ScoringService:
    """Calculate report-level values independently from validation rules."""

    _DEDUCTIONS: ClassVar[Mapping[Severity, int]] = MappingProxyType(
        {
            Severity.CRITICAL: 25,
            Severity.ERROR: 15,
            Severity.WARNING: 5,
            Severity.INFO: 0,
        }
    )

    @staticmethod
    def calculate_score(findings: Iterable[Finding]) -> int:
        """Return a score from 0 through 100 after severity deductions."""

        deductions = sum(ScoringService._DEDUCTIONS[finding.severity] for finding in findings)
        return max(0, 100 - deductions)

    @staticmethod
    def determine_grade(score: int) -> str:
        """Map a numeric score to its A-F grade."""

        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    @staticmethod
    def is_valid(findings: Iterable[Finding]) -> bool:
        """Return false only when at least one critical or error finding exists."""

        invalid_severities = {Severity.CRITICAL, Severity.ERROR}
        return all(finding.severity not in invalid_severities for finding in findings)

    @staticmethod
    def summarize(findings: Iterable[Finding]) -> ValidationSummary:
        """Count findings by severity."""

        counts = {severity: 0 for severity in Severity}
        for finding in findings:
            counts[finding.severity] += 1
        return ValidationSummary(
            critical=counts[Severity.CRITICAL],
            errors=counts[Severity.ERROR],
            warnings=counts[Severity.WARNING],
            info=counts[Severity.INFO],
        )
