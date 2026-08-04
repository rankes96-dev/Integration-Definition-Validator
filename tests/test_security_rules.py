from __future__ import annotations

import pytest

from app.models import (
    ApiKeyLocation,
    AuthType,
    IntegrationDefinition,
    ParameterLocation,
)
from app.validators.security_rules import (
    ApiKeyInQueryParameterRule,
    AuthenticationConfigurationCompletenessRule,
    AuthorizationHeaderAsNormalInputRule,
    BroadOAuthScopesRule,
    HttpsRequiredRule,
    NoEmbeddedCredentialsRule,
    SensitiveParameterDetectionRule,
)


def _replace_auth(definition: IntegrationDefinition, **updates: object) -> IntegrationDefinition:
    authentication = definition.authentication.model_copy(update=updates)
    return definition.model_copy(update={"authentication": authentication})


def _replace_command_inputs(
    definition: IntegrationDefinition, inputs: list[object]
) -> IntegrationDefinition:
    command = definition.commands[0].model_copy(update={"inputs": inputs})
    return definition.model_copy(update={"commands": [command]})


def test_sec_001_accepts_https_urls(valid_definition: IntegrationDefinition) -> None:
    assert HttpsRequiredRule().evaluate(valid_definition) == []


@pytest.mark.parametrize("base_url", ["http://localhost:8080", "http://127.0.0.1:8080"])
def test_sec_001_allows_plain_http_for_local_hosts(
    valid_definition: IntegrationDefinition, base_url: str
) -> None:
    definition = valid_definition.model_copy(update={"base_url": base_url})
    assert HttpsRequiredRule().evaluate(definition) == []


def test_sec_001_rejects_external_http_base_url(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = valid_definition.model_copy(update={"base_url": "http://api.example.com/v1"})
    findings = HttpsRequiredRule().evaluate(definition)
    assert [finding.path for finding in findings] == ["base_url"]
    assert findings[0].rule_id == "SEC-001"


def test_sec_001_checks_oauth_token_and_authorization_urls(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        token_url="http://auth.example.com/token",
        authorization_url="http://auth.example.com/authorize",
    )
    findings = HttpsRequiredRule().evaluate(definition)
    assert {finding.path for finding in findings} == {
        "authentication.token_url",
        "authentication.authorization_url",
    }


def test_sec_002_accepts_environment_and_secret_reference_names(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        credential_references=["CLIENT_ID", "MONDAY_CLIENT_SECRET_2"],
    )
    assert NoEmbeddedCredentialsRule().evaluate(definition) == []


def test_sec_002_accepts_lowercase_and_provider_secret_references(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        credential_references=[
            "monday_client_secret",
            "projects/demo/secrets/monday-client-secret",
            "VAULT:secret/monday",
        ],
    )

    assert NoEmbeddedCredentialsRule().evaluate(definition) == []


def test_sec_002_flags_token_heuristics_as_critical(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        credential_references=[
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature",
            "sk-proj-abcdefghijklmnop",
            "CLIENT_SECRET",
        ],
    )
    findings = NoEmbeddedCredentialsRule().evaluate(definition)
    assert len(findings) == 2
    assert [finding.path for finding in findings] == [
        "authentication.credential_references[0]",
        "authentication.credential_references[1]",
    ]
    assert all(finding.rule_id == "SEC-002" for finding in findings)
    assert all(finding.severity.value == "critical" for finding in findings)


def test_sec_002_flags_credentials_in_url_query_strings(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition.model_copy(
            update={"base_url": "https://api.example.com/v1?api_key=embedded-value"}
        ),
        token_url="https://auth.example.com/token?client_secret=embedded-value",
    )

    findings = NoEmbeddedCredentialsRule().evaluate(definition)

    assert {finding.path for finding in findings} == {
        "base_url",
        "authentication.token_url",
    }
    assert all(finding.rule_id == "SEC-002" for finding in findings)
    assert all("embedded-value" not in finding.message for finding in findings)


def test_sec_002_still_flags_jwt_known_prefix_and_opaque_tokens(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        credential_references=[
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature",
            "ghp_1234567890abcdefghijklmnopqrstuv",
            "aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY",
        ],
    )

    findings = NoEmbeddedCredentialsRule().evaluate(definition)

    assert len(findings) == 3
    assert all(finding.rule_id == "SEC-002" for finding in findings)


def test_sec_002_flags_url_userinfo_without_echoing_credentials(
    valid_definition: IntegrationDefinition,
) -> None:
    authentication = valid_definition.authentication.model_copy(
        update={"token_url": "https://client:secret@auth.example.com/token"}
    )
    definition = valid_definition.model_copy(
        update={
            "base_url": "https://user:password@api.example.com/v1",
            "authentication": authentication,
        }
    )

    findings = NoEmbeddedCredentialsRule().evaluate(definition)

    assert {finding.path for finding in findings} == {
        "base_url",
        "authentication.token_url",
    }
    assert all(finding.rule_id == "SEC-002" for finding in findings)
    assert all(finding.severity.value == "critical" for finding in findings)
    serialized_findings = " ".join(
        f"{finding.message} {finding.recommendation}" for finding in findings
    )
    assert "user:password" not in serialized_findings
    assert "client:secret" not in serialized_findings


def test_sec_002_accepts_normal_urls_without_userinfo(
    valid_definition: IntegrationDefinition,
) -> None:
    assert NoEmbeddedCredentialsRule().evaluate(valid_definition) == []


def test_sec_003_accepts_complete_client_credentials_config(
    valid_definition: IntegrationDefinition,
) -> None:
    assert AuthenticationConfigurationCompletenessRule().evaluate(valid_definition) == []


def test_sec_003_reports_all_missing_client_credentials_fields(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        token_url=None,
        credential_references=["CLIENT_ID"],
        scopes=[],
    )
    findings = AuthenticationConfigurationCompletenessRule().evaluate(definition)
    assert {finding.path for finding in findings} == {
        "authentication.token_url",
        "authentication.credential_references",
        "authentication.scopes",
    }


def test_sec_003_accepts_complete_authorization_code_config(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        type=AuthType.OAUTH2_AUTHORIZATION_CODE,
        authorization_url="https://auth.example.com/authorize",
    )
    assert AuthenticationConfigurationCompletenessRule().evaluate(definition) == []


def test_sec_003_requires_authorization_url_for_authorization_code(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        type=AuthType.OAUTH2_AUTHORIZATION_CODE,
        authorization_url=None,
    )
    findings = AuthenticationConfigurationCompletenessRule().evaluate(definition)
    assert [finding.path for finding in findings] == ["authentication.authorization_url"]


def test_sec_003_accepts_complete_api_key_config(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        type=AuthType.API_KEY,
        credential_references=["EXAMPLE_API_KEY"],
        api_key_name="X-API-Key",
        api_key_location=ApiKeyLocation.HEADER,
    )
    assert AuthenticationConfigurationCompletenessRule().evaluate(definition) == []


def test_sec_003_reports_all_missing_api_key_fields(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        type=AuthType.API_KEY,
        credential_references=[],
        api_key_name=None,
        api_key_location=None,
    )
    findings = AuthenticationConfigurationCompletenessRule().evaluate(definition)
    assert {finding.path for finding in findings} == {
        "authentication.api_key_name",
        "authentication.api_key_location",
        "authentication.credential_references",
    }


def test_sec_003_has_no_conditional_requirements_for_auth_none(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        type=AuthType.NONE,
        credential_references=[],
        token_url=None,
        scopes=[],
    )
    assert AuthenticationConfigurationCompletenessRule().evaluate(definition) == []


def test_sec_003_requires_one_reference_for_bearer_token(
    valid_definition: IntegrationDefinition,
) -> None:
    missing_reference = _replace_auth(
        valid_definition,
        type=AuthType.BEARER_TOKEN,
        credential_references=[],
    )
    findings = AuthenticationConfigurationCompletenessRule().evaluate(missing_reference)
    assert [finding.path for finding in findings] == ["authentication.credential_references"]

    complete = _replace_auth(
        valid_definition,
        type=AuthType.BEARER_TOKEN,
        credential_references=["api_access_token"],
    )
    assert AuthenticationConfigurationCompletenessRule().evaluate(complete) == []


def test_sec_003_requires_username_and_password_references_for_basic_auth(
    valid_definition: IntegrationDefinition,
) -> None:
    one_reference = _replace_auth(
        valid_definition,
        type=AuthType.BASIC,
        credential_references=["basic_username"],
    )
    findings = AuthenticationConfigurationCompletenessRule().evaluate(one_reference)
    assert [finding.path for finding in findings] == ["authentication.credential_references"]

    complete = _replace_auth(
        valid_definition,
        type=AuthType.BASIC,
        credential_references=["basic_username", "basic_password"],
    )
    assert AuthenticationConfigurationCompletenessRule().evaluate(complete) == []


def test_sec_004_warns_when_api_key_is_in_query(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        type=AuthType.API_KEY,
        api_key_location=ApiKeyLocation.QUERY,
    )
    findings = ApiKeyInQueryParameterRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "SEC-004"
    assert findings[0].severity.value == "warning"


def test_sec_004_accepts_header_api_key_and_ignores_non_api_key_auth(
    valid_definition: IntegrationDefinition,
) -> None:
    rule = ApiKeyInQueryParameterRule()
    header_definition = _replace_auth(
        valid_definition,
        type=AuthType.API_KEY,
        api_key_location=ApiKeyLocation.HEADER,
    )
    assert rule.evaluate(header_definition) == []

    non_api_key = _replace_auth(
        valid_definition,
        type=AuthType.BEARER_TOKEN,
        api_key_location=ApiKeyLocation.QUERY,
    )
    assert rule.evaluate(non_api_key) == []


def test_sec_005_accepts_narrow_oauth_scopes(
    valid_definition: IntegrationDefinition,
) -> None:
    assert BroadOAuthScopesRule().evaluate(valid_definition) == []


def test_sec_005_flags_each_broad_scope_case_insensitively(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_auth(
        valid_definition,
        scopes=["*", "ALL", "admin", "full_access", "boards:read"],
    )
    findings = BroadOAuthScopesRule().evaluate(definition)
    assert len(findings) == 4
    assert all(finding.rule_id == "SEC-005" for finding in findings)


def test_sec_006_accepts_non_sensitive_name_or_marked_sensitive_parameter(
    valid_definition: IntegrationDefinition,
) -> None:
    rule = SensitiveParameterDetectionRule()
    assert rule.evaluate(valid_definition) == []

    parameter = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(update={"name": "access_token", "sensitive": True})
    )
    assert rule.evaluate(_replace_command_inputs(valid_definition, [parameter])) == []


def test_sec_006_checks_both_inputs_and_outputs(
    valid_definition: IntegrationDefinition,
) -> None:
    input_parameter = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(update={"name": "access_token", "sensitive": False})
    )
    output_parameter = (
        valid_definition.commands[0]
        .outputs[0]
        .model_copy(update={"name": "client_secret", "sensitive": False})
    )
    command = valid_definition.commands[0].model_copy(
        update={"inputs": [input_parameter], "outputs": [output_parameter]}
    )
    definition = valid_definition.model_copy(update={"commands": [command]})

    findings = SensitiveParameterDetectionRule().evaluate(definition)
    assert len(findings) == 2
    assert {finding.path for finding in findings} == {
        "commands[0].inputs[0].sensitive",
        "commands[0].outputs[0].sensitive",
    }


def test_sec_007_rejects_authorization_header_case_insensitively(
    valid_definition: IntegrationDefinition,
) -> None:
    parameter = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(
            update={
                "name": "AUTHORIZATION",
                "location": ParameterLocation.HEADER,
                "sensitive": True,
            }
        )
    )
    findings = AuthorizationHeaderAsNormalInputRule().evaluate(
        _replace_command_inputs(valid_definition, [parameter])
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "SEC-007"
    assert findings[0].severity.value == "error"


def test_sec_007_ignores_authorization_outside_header_and_normal_headers(
    valid_definition: IntegrationDefinition,
) -> None:
    authorization_query = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(update={"name": "Authorization", "location": ParameterLocation.QUERY})
    )
    normal_header = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(update={"name": "X-Request-ID", "location": ParameterLocation.HEADER})
    )
    definition = _replace_command_inputs(valid_definition, [authorization_query, normal_header])
    assert AuthorizationHeaderAsNormalInputRule().evaluate(definition) == []
