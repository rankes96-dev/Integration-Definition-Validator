from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import IntegrationDefinition

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIRECTORY = PROJECT_ROOT / "examples"


def _load_example(filename: str) -> dict[str, Any]:
    with (EXAMPLES_DIRECTORY / filename).open(encoding="utf-8") as example_file:
        value: dict[str, Any] = json.load(example_file)
    return value


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    return _load_example("valid_integration.json")


@pytest.fixture
def invalid_payload() -> dict[str, Any]:
    return _load_example("invalid_integration.json")


@pytest.fixture
def valid_definition(valid_payload: dict[str, Any]) -> IntegrationDefinition:
    return IntegrationDefinition.model_validate(valid_payload)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
