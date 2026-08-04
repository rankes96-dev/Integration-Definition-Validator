"""Security validation rules (SEC-001 through SEC-007)."""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import parse_qsl, urlsplit

from app.models import (
    AuthType,
    Category,
    Finding,
    IntegrationDefinition,
    ParameterLocation,
    Severity,
)

from .base import ValidationRule, enum_value, is_blank

_LOCAL_HOSTS: Final[frozenset[str]] = frozenset({"localhost", "127.0.0.1"})
_REFERENCE_PATH_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?:\$\{[^{}]+\}|[A-Za-z][A-Za-z0-9_.-]*(?::|/)[^\s]+)$"
)
_JWT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){1,2}$")
_TOKEN_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?:Bearer\s+|Basic\s+|sk-(?:proj-)?|gh[pousr]_|github_pat_|xox[baprs]-|AIza)"
    r"[A-Za-z0-9_+/=.-]+",
    re.IGNORECASE,
)
_OPAQUE_SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?=.{32,}$)(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])[A-Za-z0-9_+/=-]+$"
)
_BROAD_SCOPES: Final[frozenset[str]] = frozenset({"*", "all", "admin", "full_access"})
_SENSITIVE_NAME_PARTS: Final[tuple[str, ...]] = (
    "token",
    "secret",
    "password",
    "api_key",
    "credential",
    "authorization",
)


def _is_secure_or_local(url: object) -> bool:
    parsed = urlsplit(str(url))
    return parsed.scheme.lower() == "https" or (parsed.hostname or "").lower() in _LOCAL_HOSTS


def _looks_like_embedded_credential(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    if _JWT_PATTERN.fullmatch(candidate) or (candidate.startswith("eyJ") and len(candidate) >= 20):
        return True
    if _TOKEN_PREFIX_PATTERN.match(candidate):
        return True
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S+$", candidate):
        return True
    if "://" in candidate and urlsplit(candidate).password is not None:
        return True
    if "PRIVATE KEY" in candidate.upper():
        return True
    if _REFERENCE_PATH_PATTERN.fullmatch(candidate):
        return False
    return bool(_OPAQUE_SECRET_PATTERN.fullmatch(candidate))


class HttpsRequiredRule(ValidationRule):
    rule_id = "SEC-001"
    category = Category.SECURITY
    default_severity = Severity.ERROR
    title = "HTTPS required"
    description = "Base, token, and authorization URLs must use HTTPS except on localhost."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings: list[Finding] = []
        urls: tuple[tuple[str, object | None], ...] = (
            ("base_url", definition.base_url),
            ("authentication.token_url", definition.authentication.token_url),
            (
                "authentication.authorization_url",
                definition.authentication.authorization_url,
            ),
        )
        for path, url in urls:
            if url is not None and not _is_secure_or_local(url):
                findings.append(
                    self.finding(
                        path=path,
                        message=f"The URL configured at '{path}' does not use HTTPS.",
                        recommendation=(
                            "Use an HTTPS URL; plain HTTP is allowed only for localhost "
                            "or 127.0.0.1."
                        ),
                    )
                )
        return findings


class NoEmbeddedCredentialsRule(ValidationRule):
    rule_id = "SEC-002"
    category = Category.SECURITY
    default_severity = Severity.CRITICAL
    title = "No embedded credentials"
    description = "Credential references must name secrets, not contain secret values."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings = [
            self.finding(
                path=f"authentication.credential_references[{index}]",
                message=("A credential value appears to be embedded directly in the definition."),
                recommendation=(
                    "Use the name of an environment variable or secret reference instead."
                ),
            )
            for index, reference in enumerate(definition.authentication.credential_references)
            if _looks_like_embedded_credential(reference)
        ]
        urls: tuple[tuple[str, object | None], ...] = (
            ("base_url", definition.base_url),
            ("authentication.token_url", definition.authentication.token_url),
            ("authentication.authorization_url", definition.authentication.authorization_url),
        )
        for path, url in urls:
            if url is None:
                continue
            parsed_url = urlsplit(str(url))
            if parsed_url.username is not None or parsed_url.password is not None:
                findings.append(
                    self.finding(
                        path=path,
                        message="A URL contains embedded authentication credentials.",
                        recommendation=(
                            "Remove URL user information and use credential references instead."
                        ),
                    )
                )
            query_keys = (key.casefold() for key, _ in parse_qsl(parsed_url.query))
            if any(
                key == "key" or any(part in key for part in _SENSITIVE_NAME_PARTS)
                for key in query_keys
            ):
                findings.append(
                    self.finding(
                        path=path,
                        message="A URL contains a credential-like query parameter.",
                        recommendation=(
                            "Remove credentials from the URL and use authentication references."
                        ),
                    )
                )
        return findings


class AuthenticationConfigurationCompletenessRule(ValidationRule):
    rule_id = "SEC-003"
    category = Category.SECURITY
    default_severity = Severity.ERROR
    title = "Authentication configuration completeness"
    description = "Authentication-specific required fields must be configured."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        authentication = definition.authentication
        requirements: list[tuple[bool, str, str, str]] = []

        if authentication.type == AuthType.OAUTH2_CLIENT_CREDENTIALS:
            requirements = [
                (
                    not is_blank(authentication.token_url),
                    "authentication.token_url",
                    "OAuth2 client credentials authentication requires a token URL.",
                    "Set authentication.token_url to the provider's HTTPS token endpoint.",
                ),
                (
                    len(authentication.credential_references) >= 2,
                    "authentication.credential_references",
                    (
                        "OAuth2 client credentials authentication requires at least "
                        "two credential references."
                    ),
                    "Reference both the client ID and client secret.",
                ),
                (
                    bool(authentication.scopes),
                    "authentication.scopes",
                    "OAuth2 client credentials authentication requires scopes.",
                    "Declare the least-privilege OAuth scopes needed by the integration.",
                ),
            ]
        elif authentication.type == AuthType.OAUTH2_AUTHORIZATION_CODE:
            requirements = [
                (
                    not is_blank(authentication.authorization_url),
                    "authentication.authorization_url",
                    "OAuth2 authorization code authentication requires an authorization URL.",
                    "Set the provider's HTTPS authorization endpoint.",
                ),
                (
                    not is_blank(authentication.token_url),
                    "authentication.token_url",
                    "OAuth2 authorization code authentication requires a token URL.",
                    "Set the provider's HTTPS token endpoint.",
                ),
                (
                    len(authentication.credential_references) >= 2,
                    "authentication.credential_references",
                    (
                        "OAuth2 authorization code authentication requires client "
                        "credential references."
                    ),
                    "Reference the client ID and client secret.",
                ),
                (
                    bool(authentication.scopes),
                    "authentication.scopes",
                    "OAuth2 authorization code authentication requires scopes.",
                    "Declare the least-privilege OAuth scopes needed by the integration.",
                ),
            ]
        elif authentication.type == AuthType.API_KEY:
            requirements = [
                (
                    not is_blank(authentication.api_key_name),
                    "authentication.api_key_name",
                    "API key authentication requires an API key name.",
                    "Set the provider's API key parameter or header name.",
                ),
                (
                    authentication.api_key_location is not None,
                    "authentication.api_key_location",
                    "API key authentication requires an API key location.",
                    "Set the API key location to 'header' or 'query'.",
                ),
                (
                    bool(authentication.credential_references),
                    "authentication.credential_references",
                    "API key authentication requires a credential reference.",
                    "Reference an environment variable or managed secret containing the API key.",
                ),
            ]
        elif authentication.type == AuthType.BEARER_TOKEN:
            requirements = [
                (
                    bool(authentication.credential_references),
                    "authentication.credential_references",
                    "Bearer token authentication requires a credential reference.",
                    "Reference the environment variable or managed secret containing the token.",
                )
            ]
        elif authentication.type == AuthType.BASIC:
            requirements = [
                (
                    len(authentication.credential_references) >= 2,
                    "authentication.credential_references",
                    "Basic authentication requires username and password references.",
                    "Reference separate environment variables or managed secrets for both values.",
                )
            ]

        return [
            self.finding(path=path, message=message, recommendation=recommendation)
            for satisfied, path, message, recommendation in requirements
            if not satisfied
        ]


class ApiKeyInQueryParameterRule(ValidationRule):
    rule_id = "SEC-004"
    category = Category.SECURITY
    default_severity = Severity.WARNING
    title = "API key in query parameter"
    description = "API keys in query strings can leak through logs and browser history."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        authentication = definition.authentication
        if (
            authentication.type == AuthType.API_KEY
            and enum_value(authentication.api_key_location) == "query"
        ):
            return [
                self.finding(
                    path="authentication.api_key_location",
                    message="The API key is configured as a query parameter.",
                    recommendation="Send the API key in a request header when supported.",
                )
            ]
        return []


class BroadOAuthScopesRule(ValidationRule):
    rule_id = "SEC-005"
    category = Category.SECURITY
    default_severity = Severity.WARNING
    title = "Broad OAuth scopes"
    description = "Broad OAuth scopes violate least-privilege access."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"authentication.scopes[{index}]",
                message=f"OAuth scope '{scope}' is overly broad.",
                recommendation="Replace it with the narrowest scopes the integration needs.",
            )
            for index, scope in enumerate(definition.authentication.scopes)
            if scope.strip().casefold() in _BROAD_SCOPES
        ]


class SensitiveParameterDetectionRule(ValidationRule):
    rule_id = "SEC-006"
    category = Category.SECURITY
    default_severity = Severity.WARNING
    title = "Sensitive parameter detection"
    description = "Parameters with security-sensitive names must be marked sensitive."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings: list[Finding] = []
        for command_index, command in enumerate(definition.commands):
            collections = (("inputs", command.inputs), ("outputs", command.outputs))
            for collection_name, parameters in collections:
                for parameter_index, parameter in enumerate(parameters):
                    normalized_name = parameter.name.casefold()
                    if (
                        any(part in normalized_name for part in _SENSITIVE_NAME_PARTS)
                        and not parameter.sensitive
                    ):
                        findings.append(
                            self.finding(
                                path=(
                                    f"commands[{command_index}].{collection_name}"
                                    f"[{parameter_index}].sensitive"
                                ),
                                message=(
                                    f"Parameter '{parameter.name}' appears sensitive but is "
                                    "not marked sensitive."
                                ),
                                recommendation="Set sensitive to true for this parameter.",
                            )
                        )
        return findings


class AuthorizationHeaderAsNormalInputRule(ValidationRule):
    rule_id = "SEC-007"
    category = Category.SECURITY
    default_severity = Severity.ERROR
    title = "Authorization header as normal input"
    description = "Authorization headers must come from authentication configuration."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings: list[Finding] = []
        for command_index, command in enumerate(definition.commands):
            findings.extend(
                self.finding(
                    path=f"commands[{command_index}].inputs[{input_index}]",
                    message=("Authorization cannot be exposed as a normal command input."),
                    recommendation=(
                        "Remove the input and generate the Authorization header from "
                        "the authentication definition."
                    ),
                )
                for input_index, parameter in enumerate(command.inputs)
                if parameter.name.casefold() == "authorization"
                and parameter.location == ParameterLocation.HEADER
            )
        return findings


SECURITY_RULES: Final[tuple[ValidationRule, ...]] = (
    HttpsRequiredRule(),
    NoEmbeddedCredentialsRule(),
    AuthenticationConfigurationCompletenessRule(),
    ApiKeyInQueryParameterRule(),
    BroadOAuthScopesRule(),
    SensitiveParameterDetectionRule(),
    AuthorizationHeaderAsNormalInputRule(),
)

AuthenticationCompletenessRule = AuthenticationConfigurationCompletenessRule
ApiKeyInQueryRule = ApiKeyInQueryParameterRule
SensitiveParameterRule = SensitiveParameterDetectionRule
AuthorizationHeaderInputRule = AuthorizationHeaderAsNormalInputRule
