from __future__ import annotations

import pytest

from app.models import HttpMethod, IntegrationDefinition
from app.validators.reliability_rules import (
    HighTimeoutRule,
    InvalidRetryStatusCodesRule,
    RetryAttemptsLimitRule,
    RetryPolicyRecommendedRule,
    TimeoutRequiredRule,
    UnsafeRetryRule,
)


def _replace_retry(definition: IntegrationDefinition, **updates: object) -> IntegrationDefinition:
    assert definition.retry_policy is not None
    retry_policy = definition.retry_policy.model_copy(update=updates)
    return definition.model_copy(update={"retry_policy": retry_policy})


@pytest.mark.parametrize("timeout", [1, 15, 60])
def test_rel_001_accepts_timeout_bounds(
    valid_definition: IntegrationDefinition, timeout: int
) -> None:
    definition = valid_definition.model_copy(update={"timeout_seconds": timeout})
    assert TimeoutRequiredRule().evaluate(definition) == []


@pytest.mark.parametrize("timeout", [None, 0, 61])
def test_rel_001_rejects_missing_or_out_of_range_timeout(
    valid_definition: IntegrationDefinition, timeout: int | None
) -> None:
    definition = valid_definition.model_copy(update={"timeout_seconds": timeout})
    findings = TimeoutRequiredRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "REL-001"
    assert findings[0].severity.value == "error"


@pytest.mark.parametrize("timeout", [1, 30])
def test_rel_002_accepts_timeout_at_or_below_thirty(
    valid_definition: IntegrationDefinition, timeout: int
) -> None:
    definition = valid_definition.model_copy(update={"timeout_seconds": timeout})
    assert HighTimeoutRule().evaluate(definition) == []


def test_rel_002_warns_above_thirty_seconds(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = valid_definition.model_copy(update={"timeout_seconds": 31})
    findings = HighTimeoutRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "REL-002"


def test_rel_003_accepts_defined_policy(valid_definition: IntegrationDefinition) -> None:
    assert RetryPolicyRecommendedRule().evaluate(valid_definition) == []


def test_rel_003_warns_for_external_integration_without_policy(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = valid_definition.model_copy(update={"retry_policy": None})
    findings = RetryPolicyRecommendedRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "REL-003"


@pytest.mark.parametrize("base_url", ["http://localhost:8080", "http://127.0.0.1"])
def test_rel_003_does_not_require_retries_for_localhost(
    valid_definition: IntegrationDefinition, base_url: str
) -> None:
    definition = valid_definition.model_copy(update={"base_url": base_url, "retry_policy": None})
    assert RetryPolicyRecommendedRule().evaluate(definition) == []


def test_rel_004_accepts_idempotent_or_safe_methods(
    valid_definition: IntegrationDefinition,
) -> None:
    rule = UnsafeRetryRule()
    assert rule.evaluate(valid_definition) == []

    for method in (HttpMethod.GET, HttpMethod.PUT):
        command = valid_definition.commands[0].model_copy(
            update={"method": method, "idempotency_key_supported": False}
        )
        definition = valid_definition.model_copy(update={"commands": [command]})
        assert rule.evaluate(definition) == []


def test_rel_004_warns_for_each_unsafe_non_idempotent_method(
    valid_definition: IntegrationDefinition,
) -> None:
    commands = [
        valid_definition.commands[0].model_copy(
            update={
                "name": f"unsafe_{method.value.lower()}",
                "method": method,
                "idempotency_key_supported": False,
            }
        )
        for method in (HttpMethod.POST, HttpMethod.PATCH, HttpMethod.DELETE)
    ]
    definition = valid_definition.model_copy(update={"commands": commands})
    findings = UnsafeRetryRule().evaluate(definition)
    assert len(findings) == 3
    assert all(finding.rule_id == "REL-004" for finding in findings)


def test_rel_004_ignores_disabled_retry_policy(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_retry(valid_definition, enabled=False)
    command = definition.commands[0].model_copy(update={"idempotency_key_supported": False})
    definition = definition.model_copy(update={"commands": [command]})
    assert UnsafeRetryRule().evaluate(definition) == []


def test_rel_005_accepts_transient_retry_status_codes(
    valid_definition: IntegrationDefinition,
) -> None:
    assert InvalidRetryStatusCodesRule().evaluate(valid_definition) == []


def test_rel_005_warns_for_each_disallowed_status_code(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_retry(
        valid_definition, retry_on_status_codes=[400, 401, 403, 404, 429, 500]
    )
    findings = InvalidRetryStatusCodesRule().evaluate(definition)
    assert len(findings) == 4
    assert [finding.path for finding in findings] == [
        "retry_policy.retry_on_status_codes[0]",
        "retry_policy.retry_on_status_codes[1]",
        "retry_policy.retry_on_status_codes[2]",
        "retry_policy.retry_on_status_codes[3]",
    ]


def test_rel_005_flags_policy_covering_every_http_status(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_retry(
        valid_definition,
        retry_on_status_codes=list(range(100, 600)),
    )

    findings = InvalidRetryStatusCodesRule().evaluate(definition)

    broad_finding = next(
        finding for finding in findings if finding.path == "retry_policy.retry_on_status_codes"
    )
    assert broad_finding.rule_id == "REL-005"
    assert "every HTTP status code" in broad_finding.message


def test_rel_005_ignores_status_codes_when_retries_are_disabled(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_retry(
        valid_definition,
        enabled=False,
        retry_on_status_codes=[400, 401, 403, 404],
    )
    assert InvalidRetryStatusCodesRule().evaluate(definition) == []


def test_rel_006_accepts_five_attempts(valid_definition: IntegrationDefinition) -> None:
    definition = _replace_retry(valid_definition, max_attempts=5)
    assert RetryAttemptsLimitRule().evaluate(definition) == []


def test_rel_006_reports_constructed_value_over_limit(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_retry(valid_definition, max_attempts=6)
    findings = RetryAttemptsLimitRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "REL-006"
    assert findings[0].severity.value == "error"
