from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.rules import get_validation_service
from app.main import app
from app.models import IntegrationDefinition, SchemaValidationErrorResponse


def _finding_ids(report: dict[str, Any]) -> set[str]:
    return {finding["rule_id"] for finding in report["findings"]}


def test_valid_definition_returns_perfect_report(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 200
    report = response.json()
    UUID(report["validation_id"])
    assert report["validated_at"].endswith(("Z", "+00:00"))
    assert report["integration_name"] == valid_payload["name"]
    assert report["valid"] is True
    assert report["score"] == 100
    assert report["grade"] == "A"
    assert report["summary"] == {
        "critical": 0,
        "errors": 0,
        "warnings": 0,
        "info": 0,
    }
    assert report["findings"] == []


def test_semantic_warning_returns_200_and_remains_valid(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    valid_payload.pop("owner")

    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 200
    report = response.json()
    assert report["valid"] is True
    assert report["score"] == 95
    assert report["grade"] == "A"
    assert report["summary"]["warnings"] == 1
    assert _finding_ids(report) == {"DOC-005"}


def test_semantic_error_returns_200_and_invalid_report(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    valid_payload["base_url"] = "http://api.example.com/v1"

    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 200
    report = response.json()
    assert report["valid"] is False
    assert report["score"] == 85
    assert report["grade"] == "B"
    assert report["summary"]["errors"] == 1
    assert _finding_ids(report) == {"SEC-001"}


def test_invalid_example_returns_actionable_multi_category_report(
    client: TestClient, invalid_payload: dict[str, Any]
) -> None:
    response = client.post("/api/v1/validate", json=invalid_payload)

    assert response.status_code == 200
    report = response.json()
    assert report["valid"] is False
    assert 0 <= report["score"] < 100
    assert report["summary"]["critical"] >= 1
    assert report["summary"]["errors"] >= 1
    assert report["summary"]["warnings"] >= 1
    assert {"SEC-001", "SEC-002", "API-001", "REL-002"}.issubset(_finding_ids(report))
    assert all(finding["recommendation"] for finding in report["findings"])


def test_missing_required_field_returns_custom_422(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    valid_payload.pop("name")

    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "schema_validation_failed"
    assert body["message"] == ("The integration definition does not match the required schema")
    assert any(detail["path"] == "name" for detail in body["details"])


def test_invalid_enum_returns_dotted_schema_error_path(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    valid_payload["commands"][0]["method"] = "CONNECT"

    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 422
    details = response.json()["details"]
    method_error = next(detail for detail in details if detail["path"] == "commands.0.method")
    assert "GET" in method_error["message"]
    assert "DELETE" in method_error["message"]


def test_schema_error_preserves_nested_path_field_name(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    valid_payload["commands"][0]["path"] = ""

    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 422
    assert any(detail["path"] == "commands.0.path" for detail in response.json()["details"])


def test_schema_error_bounds_extremely_long_unknown_field_details(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    valid_payload["x" * 1_500] = True

    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 422
    parsed = SchemaValidationErrorResponse.model_validate(response.json())
    assert parsed.error == "schema_validation_failed"
    assert all(len(detail.path) <= 1_000 for detail in parsed.details)
    assert all(len(detail.message) <= 1_000 for detail in parsed.details)


def test_long_semantically_invalid_path_returns_bounded_finding(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    valid_payload["commands"][0]["path"] = "x" * 1_500

    response = client.post("/api/v1/validate", json=valid_payload)

    assert response.status_code == 200
    report = response.json()
    assert "API-003" in _finding_ids(report)
    assert report["valid"] is False
    assert all(len(finding["path"]) <= 500 for finding in report["findings"])
    assert all(len(finding["message"]) <= 1_000 for finding in report["findings"])
    assert all(len(finding["recommendation"]) <= 1_000 for finding in report["findings"])


def test_oversized_request_body_is_rejected_before_validation(client: TestClient) -> None:
    oversized_body = b"{" + b"x" * (256 * 1024) + b"}"

    response = client.post(
        "/api/v1/validate",
        content=oversized_body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "error": "request_body_too_large",
        "message": "Request body must not exceed 262144 bytes",
    }


class _ExplodingValidationService:
    def validate(self, definition: IntegrationDefinition) -> NoReturn:
        del definition
        raise RuntimeError("internal-sensitive-detail")


def test_unexpected_exception_returns_sanitized_500(
    valid_payload: dict[str, Any],
) -> None:
    app.dependency_overrides[get_validation_service] = _ExplodingValidationService
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.post("/api/v1/validate", json=valid_payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {
        "error": "internal_server_error",
        "message": "The validation request could not be completed",
    }
    assert "internal-sensitive-detail" not in response.text


def test_rules_endpoint_lists_the_complete_unique_catalog(client: TestClient) -> None:
    response = client.get("/api/v1/rules")

    assert response.status_code == 200
    rules = response.json()["rules"]
    expected_ids = {
        *(f"API-{number:03d}" for number in range(1, 8)),
        *(f"SEC-{number:03d}" for number in range(1, 8)),
        *(f"REL-{number:03d}" for number in range(1, 7)),
        *(f"TEST-{number:03d}" for number in range(1, 5)),
        *(f"DOC-{number:03d}" for number in range(1, 6)),
    }
    assert len(rules) == 29
    assert {rule["id"] for rule in rules} == expected_ids
    assert len({rule["id"] for rule in rules}) == len(rules)
    assert all(rule["title"] and rule["description"] for rule in rules)
    assert all(rule["severity"] in {"critical", "error", "warning", "info"} for rule in rules)
