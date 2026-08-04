from __future__ import annotations

import pytest

from app.models import Category, Finding, Severity
from app.services.scoring_service import ScoringService


def _finding(severity: Severity, index: int = 1) -> Finding:
    return Finding(
        rule_id=f"TEST-{index:03d}",
        severity=severity,
        category=Category.TESTING,
        path="commands[0]",
        message="Test finding",
        recommendation="Resolve the test finding",
    )


def test_score_deducts_points_by_severity() -> None:
    findings = [
        _finding(Severity.CRITICAL, 1),
        _finding(Severity.ERROR, 2),
        _finding(Severity.WARNING, 3),
        _finding(Severity.INFO, 4),
    ]

    assert ScoringService.calculate_score(findings) == 55


def test_score_never_falls_below_zero() -> None:
    findings = [_finding(Severity.CRITICAL, index) for index in range(1, 6)]

    assert ScoringService.calculate_score(findings) == 0


@pytest.mark.parametrize(
    ("score", "grade"),
    [
        (100, "A"),
        (90, "A"),
        (89, "B"),
        (80, "B"),
        (79, "C"),
        (70, "C"),
        (69, "D"),
        (60, "D"),
        (59, "F"),
        (0, "F"),
    ],
)
def test_grade_boundaries(score: int, grade: str) -> None:
    assert ScoringService.determine_grade(score) == grade


def test_validity_ignores_warnings_and_info() -> None:
    findings = [_finding(Severity.WARNING), _finding(Severity.INFO, 2)]

    assert ScoringService.is_valid(findings) is True


@pytest.mark.parametrize("severity", [Severity.CRITICAL, Severity.ERROR])
def test_critical_and_error_findings_are_invalid(severity: Severity) -> None:
    assert ScoringService.is_valid([_finding(severity)]) is False


def test_summary_counts_every_severity() -> None:
    summary = ScoringService.summarize(
        [
            _finding(Severity.CRITICAL, 1),
            _finding(Severity.ERROR, 2),
            _finding(Severity.ERROR, 3),
            _finding(Severity.WARNING, 4),
            _finding(Severity.WARNING, 5),
            _finding(Severity.WARNING, 6),
            _finding(Severity.INFO, 7),
        ]
    )

    assert summary.model_dump() == {
        "critical": 1,
        "errors": 2,
        "warnings": 3,
        "info": 1,
    }


def test_empty_findings_produce_perfect_valid_result() -> None:
    assert ScoringService.calculate_score([]) == 100
    assert ScoringService.determine_grade(100) == "A"
    assert ScoringService.is_valid([]) is True
    assert ScoringService.summarize([]).model_dump() == {
        "critical": 0,
        "errors": 0,
        "warnings": 0,
        "info": 0,
    }
