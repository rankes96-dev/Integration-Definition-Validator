"""Test-coverage validation rules (TEST-001 through TEST-004)."""

from __future__ import annotations

from typing import Final

from app.models import (
    AuthType,
    Category,
    Finding,
    IntegrationDefinition,
    Severity,
    TestCaseType,
)

from .base import ValidationRule


def _has_test_type(definition: IntegrationDefinition, test_type: TestCaseType) -> bool:
    return any(
        test_case.type == test_type
        for command in definition.commands
        for test_case in command.test_cases
    )


class SuccessTestRequiredRule(ValidationRule):
    rule_id = "TEST-001"
    category = Category.TESTING
    default_severity = Severity.WARNING
    title = "Success test required"
    description = "Every command should include a success test case."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"commands[{index}].test_cases",
                message=f"Command '{command.name}' has no success test case.",
                recommendation="Add a test case whose type is 'success'.",
            )
            for index, command in enumerate(definition.commands)
            if not any(test_case.type == TestCaseType.SUCCESS for test_case in command.test_cases)
        ]


class AuthenticationFailureTestRule(ValidationRule):
    rule_id = "TEST-002"
    category = Category.TESTING
    default_severity = Severity.WARNING
    title = "Authentication failure test"
    description = "Authenticated integrations should include an auth-failure test."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        if definition.authentication.type != AuthType.NONE and not _has_test_type(
            definition, TestCaseType.AUTH_FAILURE
        ):
            return [
                self.finding(
                    path="commands",
                    message="The authenticated integration has no auth_failure test case.",
                    recommendation="Add at least one test case whose type is 'auth_failure'.",
                )
            ]
        return []


class ServerFailureTestRule(ValidationRule):
    rule_id = "TEST-003"
    category = Category.TESTING
    default_severity = Severity.WARNING
    title = "Server failure test"
    description = "Integrations should include a server-error test."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        if not _has_test_type(definition, TestCaseType.SERVER_ERROR):
            return [
                self.finding(
                    path="commands",
                    message="The integration has no server_error test case.",
                    recommendation="Add at least one test case whose type is 'server_error'.",
                )
            ]
        return []


class TimeoutTestRule(ValidationRule):
    rule_id = "TEST-004"
    category = Category.TESTING
    default_severity = Severity.WARNING
    title = "Timeout test"
    description = "Integrations with retries enabled should include a timeout test."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        retry_policy = definition.retry_policy
        if (
            retry_policy is not None
            and retry_policy.enabled
            and not _has_test_type(definition, TestCaseType.TIMEOUT)
        ):
            return [
                self.finding(
                    path="commands",
                    message="Retries are enabled but there is no timeout test case.",
                    recommendation="Add at least one test case whose type is 'timeout'.",
                )
            ]
        return []


TESTING_RULES: Final[tuple[ValidationRule, ...]] = (
    SuccessTestRequiredRule(),
    AuthenticationFailureTestRule(),
    ServerFailureTestRule(),
    TimeoutTestRule(),
)
