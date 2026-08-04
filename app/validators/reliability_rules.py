"""Reliability validation rules (REL-001 through REL-006)."""

from __future__ import annotations

from typing import Final
from urllib.parse import urlsplit

from app.models import Category, Finding, HttpMethod, IntegrationDefinition, Severity

from .base import ValidationRule

_LOCAL_HOSTS: Final[frozenset[str]] = frozenset({"localhost", "127.0.0.1"})
_UNSAFE_RETRY_METHODS: Final[frozenset[HttpMethod]] = frozenset(
    {HttpMethod.POST, HttpMethod.PATCH, HttpMethod.DELETE}
)
_INVALID_RETRY_CODES: Final[frozenset[int]] = frozenset({400, 401, 403, 404})
_ALL_HTTP_STATUS_CODES: Final[frozenset[int]] = frozenset(range(100, 600))


class TimeoutRequiredRule(ValidationRule):
    rule_id = "REL-001"
    category = Category.RELIABILITY
    default_severity = Severity.ERROR
    title = "Timeout required"
    description = "The integration timeout must be between 1 and 60 seconds."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        timeout = definition.timeout_seconds
        if timeout is None or not 1 <= timeout <= 60:
            return [
                self.finding(
                    path="timeout_seconds",
                    message="Timeout must be between 1 and 60 seconds.",
                    recommendation="Set timeout_seconds to a value from 1 through 60.",
                )
            ]
        return []


class HighTimeoutRule(ValidationRule):
    rule_id = "REL-002"
    category = Category.RELIABILITY
    default_severity = Severity.WARNING
    title = "High timeout"
    description = "Timeouts above 30 seconds can reduce service responsiveness."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        timeout = definition.timeout_seconds
        if timeout is not None and timeout > 30:
            return [
                self.finding(
                    path="timeout_seconds",
                    message=f"The configured timeout of {timeout} seconds is high.",
                    recommendation="Use a timeout of 30 seconds or less when possible.",
                )
            ]
        return []


class RetryPolicyRecommendedRule(ValidationRule):
    rule_id = "REL-003"
    category = Category.RELIABILITY
    default_severity = Severity.WARNING
    title = "Retry policy recommended"
    description = "External integrations should define a retry policy."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        hostname = (urlsplit(str(definition.base_url)).hostname or "").lower()
        if hostname not in _LOCAL_HOSTS and definition.retry_policy is None:
            return [
                self.finding(
                    path="retry_policy",
                    message="This external integration has no retry policy.",
                    recommendation=(
                        "Define a bounded retry policy for transient upstream failures."
                    ),
                )
            ]
        return []


class UnsafeRetryRule(ValidationRule):
    rule_id = "REL-004"
    category = Category.RELIABILITY
    default_severity = Severity.WARNING
    title = "Unsafe retry"
    description = "Mutating requests should not be retried without idempotency protection."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        retry_policy = definition.retry_policy
        if retry_policy is None or not retry_policy.enabled:
            return []
        return [
            self.finding(
                path=f"commands[{index}].idempotency_key_supported",
                message=(
                    f"{command.method.value} command '{command.name}' may be retried "
                    "without idempotency protection."
                ),
                recommendation=(
                    "Enable idempotency-key support or disable automatic retries for "
                    "this operation."
                ),
            )
            for index, command in enumerate(definition.commands)
            if command.method in _UNSAFE_RETRY_METHODS and not command.idempotency_key_supported
        ]


class InvalidRetryStatusCodesRule(ValidationRule):
    rule_id = "REL-005"
    category = Category.RELIABILITY
    default_severity = Severity.WARNING
    title = "Invalid retry status codes"
    description = "Client and authentication failures must not be retried automatically."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        retry_policy = definition.retry_policy
        if retry_policy is None or not retry_policy.enabled:
            return []
        findings = [
            self.finding(
                path=f"retry_policy.retry_on_status_codes[{index}]",
                message=f"Status code {status_code} should not be retried automatically.",
                recommendation="Remove 400, 401, 403, and 404 from retry status codes.",
            )
            for index, status_code in enumerate(retry_policy.retry_on_status_codes)
            if status_code in _INVALID_RETRY_CODES
        ]
        if _ALL_HTTP_STATUS_CODES.issubset(retry_policy.retry_on_status_codes):
            findings.append(
                self.finding(
                    path="retry_policy.retry_on_status_codes",
                    message="The retry policy is configured for every HTTP status code.",
                    recommendation="Retry only explicitly selected transient failure status codes.",
                )
            )
        return findings


class RetryAttemptsLimitRule(ValidationRule):
    rule_id = "REL-006"
    category = Category.RELIABILITY
    default_severity = Severity.ERROR
    title = "Retry attempts limit"
    description = "A retry policy cannot allow more than five attempts."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        retry_policy = definition.retry_policy
        if retry_policy is not None and retry_policy.max_attempts > 5:
            return [
                self.finding(
                    path="retry_policy.max_attempts",
                    message="Retry max_attempts cannot be greater than 5.",
                    recommendation="Set max_attempts to 5 or less.",
                )
            ]
        return []


RELIABILITY_RULES: Final[tuple[ValidationRule, ...]] = (
    TimeoutRequiredRule(),
    HighTimeoutRule(),
    RetryPolicyRecommendedRule(),
    UnsafeRetryRule(),
    InvalidRetryStatusCodesRule(),
    RetryAttemptsLimitRule(),
)
