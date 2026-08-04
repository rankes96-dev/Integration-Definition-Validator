"""Public validation-rule API and immutable default rule registry."""

from __future__ import annotations

from typing import Final

from .base import ValidationRule
from .documentation_rules import (
    DOCUMENTATION_RULES,
    CommandDescriptionRule,
    InputDescriptionRule,
    IntegrationDescriptionRule,
    OutputDefinitionsRule,
    OwnerRule,
)
from .reliability_rules import (
    RELIABILITY_RULES,
    HighTimeoutRule,
    InvalidRetryStatusCodesRule,
    RetryAttemptsLimitRule,
    RetryPolicyRecommendedRule,
    TimeoutRequiredRule,
    UnsafeRetryRule,
)
from .schema_rules import (
    SCHEMA_RULES,
    ExpectedSuccessStatusRule,
    NoBodyOnGetRule,
    PathMustStartWithSlashRule,
    PathParameterConsistencyRule,
    PathStartsWithSlashRule,
    UniqueCommandNamesRule,
    UniqueInputNamesRule,
    ValidCommandNameRule,
)
from .security_rules import (
    SECURITY_RULES,
    ApiKeyInQueryParameterRule,
    ApiKeyInQueryRule,
    AuthenticationCompletenessRule,
    AuthenticationConfigurationCompletenessRule,
    AuthorizationHeaderAsNormalInputRule,
    AuthorizationHeaderInputRule,
    BroadOAuthScopesRule,
    HttpsRequiredRule,
    NoEmbeddedCredentialsRule,
    SensitiveParameterDetectionRule,
    SensitiveParameterRule,
)
from .testing_rules import (
    TESTING_RULES,
    AuthenticationFailureTestRule,
    ServerFailureTestRule,
    SuccessTestRequiredRule,
    TimeoutTestRule,
)

RULE_TYPES: Final[tuple[type[ValidationRule], ...]] = (
    UniqueCommandNamesRule,
    ValidCommandNameRule,
    PathMustStartWithSlashRule,
    UniqueInputNamesRule,
    PathParameterConsistencyRule,
    NoBodyOnGetRule,
    ExpectedSuccessStatusRule,
    HttpsRequiredRule,
    NoEmbeddedCredentialsRule,
    AuthenticationConfigurationCompletenessRule,
    ApiKeyInQueryParameterRule,
    BroadOAuthScopesRule,
    SensitiveParameterDetectionRule,
    AuthorizationHeaderAsNormalInputRule,
    TimeoutRequiredRule,
    HighTimeoutRule,
    RetryPolicyRecommendedRule,
    UnsafeRetryRule,
    InvalidRetryStatusCodesRule,
    RetryAttemptsLimitRule,
    SuccessTestRequiredRule,
    AuthenticationFailureTestRule,
    ServerFailureTestRule,
    TimeoutTestRule,
    IntegrationDescriptionRule,
    CommandDescriptionRule,
    InputDescriptionRule,
    OutputDefinitionsRule,
    OwnerRule,
)


def get_default_rules() -> tuple[ValidationRule, ...]:
    """Return a fresh immutable collection containing every default rule."""
    return tuple(rule_type() for rule_type in RULE_TYPES)


def get_all_rules() -> tuple[ValidationRule, ...]:
    """Return all validation rules in deterministic execution order."""
    return get_default_rules()


DEFAULT_RULES: Final[tuple[ValidationRule, ...]] = (
    *SCHEMA_RULES,
    *SECURITY_RULES,
    *RELIABILITY_RULES,
    *TESTING_RULES,
    *DOCUMENTATION_RULES,
)
ALL_RULES: Final[tuple[ValidationRule, ...]] = DEFAULT_RULES
RULES: Final[tuple[ValidationRule, ...]] = DEFAULT_RULES

__all__ = [
    "ALL_RULES",
    "DEFAULT_RULES",
    "DOCUMENTATION_RULES",
    "RELIABILITY_RULES",
    "RULES",
    "RULE_TYPES",
    "SCHEMA_RULES",
    "SECURITY_RULES",
    "TESTING_RULES",
    "ApiKeyInQueryParameterRule",
    "ApiKeyInQueryRule",
    "AuthenticationCompletenessRule",
    "AuthenticationConfigurationCompletenessRule",
    "AuthenticationFailureTestRule",
    "AuthorizationHeaderAsNormalInputRule",
    "AuthorizationHeaderInputRule",
    "BroadOAuthScopesRule",
    "CommandDescriptionRule",
    "ExpectedSuccessStatusRule",
    "HighTimeoutRule",
    "HttpsRequiredRule",
    "InputDescriptionRule",
    "IntegrationDescriptionRule",
    "InvalidRetryStatusCodesRule",
    "NoBodyOnGetRule",
    "NoEmbeddedCredentialsRule",
    "OutputDefinitionsRule",
    "OwnerRule",
    "PathMustStartWithSlashRule",
    "PathParameterConsistencyRule",
    "PathStartsWithSlashRule",
    "RetryAttemptsLimitRule",
    "RetryPolicyRecommendedRule",
    "SensitiveParameterDetectionRule",
    "SensitiveParameterRule",
    "ServerFailureTestRule",
    "SuccessTestRequiredRule",
    "TimeoutRequiredRule",
    "TimeoutTestRule",
    "UniqueCommandNamesRule",
    "UniqueInputNamesRule",
    "UnsafeRetryRule",
    "ValidCommandNameRule",
    "ValidationRule",
    "get_all_rules",
    "get_default_rules",
]
