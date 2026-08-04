from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from app.models import IntegrationDefinition


def _assert_invalid(payload: dict[str, Any], path_fragment: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        IntegrationDefinition.model_validate(payload)
    paths = {".".join(str(part) for part in error["loc"]) for error in exc_info.value.errors()}
    assert any(path_fragment in path for path in paths)


@pytest.mark.parametrize("name", ["ab", "x" * 101])
def test_integration_name_length_is_bounded(valid_payload: dict[str, Any], name: str) -> None:
    valid_payload["name"] = name
    _assert_invalid(valid_payload, "name")


def test_description_is_limited_to_500_characters(valid_payload: dict[str, Any]) -> None:
    valid_payload["description"] = "x" * 501
    _assert_invalid(valid_payload, "description")


@pytest.mark.parametrize("timeout", [0, 61, 1.5, "15", True])
def test_timeout_is_a_strict_integer_between_one_and_sixty(
    valid_payload: dict[str, Any], timeout: object
) -> None:
    valid_payload["timeout_seconds"] = timeout
    _assert_invalid(valid_payload, "timeout_seconds")


@pytest.mark.parametrize("attempts", [0, 6])
def test_retry_attempts_are_bounded(valid_payload: dict[str, Any], attempts: int) -> None:
    valid_payload["retry_policy"]["max_attempts"] = attempts
    _assert_invalid(valid_payload, "retry_policy.max_attempts")


def test_at_least_one_command_is_required(valid_payload: dict[str, Any]) -> None:
    valid_payload["commands"] = []
    _assert_invalid(valid_payload, "commands")


def test_command_count_is_limited_to_100(valid_payload: dict[str, Any]) -> None:
    command = deepcopy(valid_payload["commands"][0])
    valid_payload["commands"] = [deepcopy(command) for _ in range(101)]
    _assert_invalid(valid_payload, "commands")


@pytest.mark.parametrize("collection_name", ["inputs", "outputs"])
def test_parameter_collections_are_limited_to_100(
    valid_payload: dict[str, Any], collection_name: str
) -> None:
    command = valid_payload["commands"][0]
    parameter = deepcopy(command[collection_name][0])
    command[collection_name] = [deepcopy(parameter) for _ in range(101)]
    _assert_invalid(valid_payload, f"commands.0.{collection_name}")


def test_test_cases_are_limited_to_50(valid_payload: dict[str, Any]) -> None:
    test_case = deepcopy(valid_payload["commands"][0]["test_cases"][0])
    valid_payload["commands"][0]["test_cases"] = [deepcopy(test_case) for _ in range(51)]
    _assert_invalid(valid_payload, "commands.0.test_cases")


def test_tags_must_be_unique(valid_payload: dict[str, Any]) -> None:
    valid_payload["tags"] = ["monday", "monday"]
    _assert_invalid(valid_payload, "tags")


def test_unknown_fields_are_rejected(valid_payload: dict[str, Any]) -> None:
    valid_payload["persist_request"] = True
    _assert_invalid(valid_payload, "persist_request")


def test_status_codes_are_strict_and_in_http_range(valid_payload: dict[str, Any]) -> None:
    valid_payload["commands"][0]["expected_status_codes"] = [99, 600, "200"]
    _assert_invalid(valid_payload, "commands.0.expected_status_codes")
