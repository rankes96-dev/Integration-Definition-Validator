"""Orchestration of validation rules and report generation."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from app.models import IntegrationDefinition, RuleMetadata, ValidationResponse
from app.services.scoring_service import ScoringService
from app.validators import ValidationRule, get_default_rules

logger = logging.getLogger("app.validation")


class ValidationService:
    """Run stateless validation rules and build a complete response."""

    def __init__(self, rules: Sequence[ValidationRule] | None = None) -> None:
        self._rules = tuple(rules) if rules is not None else get_default_rules()

    def validate(self, definition: IntegrationDefinition) -> ValidationResponse:
        """Evaluate every rule and calculate the final validation report."""

        started_at = perf_counter()
        validation_id = uuid4()
        findings = [finding for rule in self._rules for finding in rule.evaluate(definition)]
        score = ScoringService.calculate_score(findings)
        summary = ScoringService.summarize(findings)
        response = ValidationResponse(
            validation_id=validation_id,
            validated_at=datetime.now(UTC),
            integration_name=definition.name,
            valid=ScoringService.is_valid(findings),
            score=score,
            grade=ScoringService.determine_grade(score),
            summary=summary,
            findings=findings,
        )
        logger.info(
            "Integration validation completed",
            extra={
                "event": "integration_validation_completed",
                "validation_id": str(validation_id),
                "integration_name": definition.name,
                "score": score,
                "critical_count": summary.critical,
                "error_count": summary.errors,
                "warning_count": summary.warnings,
                "duration_ms": round((perf_counter() - started_at) * 1000, 3),
            },
        )
        return response

    def list_rules(self) -> list[RuleMetadata]:
        """Return public metadata for every enabled rule."""

        return [
            RuleMetadata(
                id=rule.rule_id,
                category=rule.category,
                severity=rule.default_severity,
                title=rule.title,
                description=rule.description,
            )
            for rule in self._rules
        ]
