from __future__ import annotations

from typing import Any

from app.models import Category, Finding, IntegrationDefinition, Severity
from app.services.validation_service import ValidationService
from app.validators.base import ValidationRule


class _StubRule(ValidationRule):
    rule_id = "TEST-999"
    category = Category.TESTING
    default_severity = Severity.WARNING
    title = "Stub rule"
    description = "Produces one deterministic finding for orchestration tests."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        del definition
        return [
            self.finding(
                path="commands[0]",
                message="Stub finding",
                recommendation="Use the stub recommendation",
            )
        ]


def test_service_runs_injected_rules_and_builds_response(
    valid_definition: IntegrationDefinition,
) -> None:
    response = ValidationService(rules=[_StubRule()]).validate(valid_definition)

    assert response.integration_name == valid_definition.name
    assert response.valid is True
    assert response.score == 95
    assert response.grade == "A"
    assert response.summary.warnings == 1
    assert [finding.rule_id for finding in response.findings] == ["TEST-999"]
    assert response.validated_at.tzinfo is not None


def test_service_accepts_an_explicit_empty_rule_set(
    valid_definition: IntegrationDefinition,
) -> None:
    response = ValidationService(rules=[]).validate(valid_definition)

    assert response.score == 100
    assert response.valid is True
    assert response.findings == []


def test_list_rules_maps_rule_metadata() -> None:
    assert ValidationService(rules=[_StubRule()]).list_rules()[0].model_dump(mode="json") == {
        "id": "TEST-999",
        "category": "testing",
        "severity": "warning",
        "title": "Stub rule",
        "description": "Produces one deterministic finding for orchestration tests.",
    }


def test_validation_log_contains_metadata_but_not_definition(
    monkeypatch: Any, valid_definition: IntegrationDefinition
) -> None:
    logged: dict[str, object] = {}

    def capture_log(message: str, *, extra: dict[str, object]) -> None:
        logged["message"] = message
        logged.update(extra)

    monkeypatch.setattr("app.services.validation_service.logger.info", capture_log)

    ValidationService(rules=[]).validate(valid_definition)

    assert logged["event"] == "integration_validation_completed"
    assert logged["integration_name"] == valid_definition.name
    assert logged["score"] == 100
    assert "credential_references" not in logged
    assert "commands" not in logged
    assert "request_body" not in logged
