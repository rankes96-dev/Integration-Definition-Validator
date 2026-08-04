from __future__ import annotations

from app.models import AuthType, IntegrationDefinition
from app.models import TestCaseType as CaseType
from app.validators.testing_rules import (
    AuthenticationFailureTestRule,
    ServerFailureTestRule,
    SuccessTestRequiredRule,
    TimeoutTestRule,
)


def _without_test_type(
    definition: IntegrationDefinition, test_type: CaseType
) -> IntegrationDefinition:
    command = definition.commands[0]
    test_cases = [case for case in command.test_cases if case.type != test_type]
    return definition.model_copy(
        update={"commands": [command.model_copy(update={"test_cases": test_cases})]}
    )


def test_test_001_accepts_success_test_per_command(
    valid_definition: IntegrationDefinition,
) -> None:
    assert SuccessTestRequiredRule().evaluate(valid_definition) == []


def test_test_001_warns_for_command_without_success_test(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _without_test_type(valid_definition, CaseType.SUCCESS)
    findings = SuccessTestRequiredRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "TEST-001"
    assert findings[0].path == "commands[0].test_cases"


def test_test_001_evaluates_each_command_independently(
    valid_definition: IntegrationDefinition,
) -> None:
    first = valid_definition.commands[0]
    second = first.model_copy(update={"name": "second_command", "test_cases": []})
    definition = valid_definition.model_copy(update={"commands": [first, second]})
    findings = SuccessTestRequiredRule().evaluate(definition)
    assert [finding.path for finding in findings] == ["commands[1].test_cases"]


def test_test_002_accepts_auth_failure_test(valid_definition: IntegrationDefinition) -> None:
    assert AuthenticationFailureTestRule().evaluate(valid_definition) == []


def test_test_002_warns_for_authenticated_integration_without_failure_test(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _without_test_type(valid_definition, CaseType.AUTH_FAILURE)
    findings = AuthenticationFailureTestRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "TEST-002"


def test_test_002_does_not_require_failure_test_when_auth_is_none(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _without_test_type(valid_definition, CaseType.AUTH_FAILURE)
    authentication = definition.authentication.model_copy(update={"type": AuthType.NONE})
    definition = definition.model_copy(update={"authentication": authentication})
    assert AuthenticationFailureTestRule().evaluate(definition) == []


def test_test_003_accepts_server_error_test(valid_definition: IntegrationDefinition) -> None:
    assert ServerFailureTestRule().evaluate(valid_definition) == []


def test_test_003_warns_without_server_error_test(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _without_test_type(valid_definition, CaseType.SERVER_ERROR)
    findings = ServerFailureTestRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "TEST-003"


def test_test_004_accepts_timeout_test_when_retries_enabled(
    valid_definition: IntegrationDefinition,
) -> None:
    assert TimeoutTestRule().evaluate(valid_definition) == []


def test_test_004_warns_when_retries_enabled_without_timeout_test(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _without_test_type(valid_definition, CaseType.TIMEOUT)
    findings = TimeoutTestRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "TEST-004"


def test_test_004_does_not_require_timeout_test_without_enabled_retries(
    valid_definition: IntegrationDefinition,
) -> None:
    rule = TimeoutTestRule()
    definition = _without_test_type(valid_definition, CaseType.TIMEOUT)
    assert definition.retry_policy is not None
    disabled_policy = definition.retry_policy.model_copy(update={"enabled": False})
    assert rule.evaluate(definition.model_copy(update={"retry_policy": disabled_policy})) == []
    assert rule.evaluate(definition.model_copy(update={"retry_policy": None})) == []
