from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_service_identity(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "integration-definition-validator",
        "version": "1.0.0",
    }


def test_root_redirects_to_swagger(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/docs"


def test_generated_documentation_endpoints_are_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200

    schema_response = client.get("/openapi.json")
    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert "/api/v1/validate" in schema["paths"]
    assert "/api/v1/rules" in schema["paths"]
    assert "IntegrationDefinition" in schema["components"]["schemas"]
    assert "ValidationResponse" in schema["components"]["schemas"]


def test_openapi_exposes_enums_limits_and_error_responses(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]

    assert components["AuthType"]["enum"] == [
        "none",
        "api_key",
        "bearer_token",
        "basic",
        "oauth2_client_credentials",
        "oauth2_authorization_code",
    ]
    timeout_schema = components["IntegrationDefinition"]["properties"]["timeout_seconds"]
    assert timeout_schema["minimum"] == 1
    assert timeout_schema["maximum"] == 60
    validate_responses = schema["paths"]["/api/v1/validate"]["post"]["responses"]
    expected_error_schemas = {
        "413": "#/components/schemas/RequestBodyTooLargeResponse",
        "422": "#/components/schemas/SchemaValidationErrorResponse",
        "500": "#/components/schemas/InternalServerErrorResponse",
    }
    for status_code, schema_reference in expected_error_schemas.items():
        response_schema = validate_responses[status_code]["content"]["application/json"]["schema"]
        assert response_schema == {"$ref": schema_reference}
