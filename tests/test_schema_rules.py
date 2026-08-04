from __future__ import annotations

import pytest

from app.models import (
    HttpMethod,
    IntegrationDefinition,
    ParameterLocation,
)
from app.validators.schema_rules import (
    ExpectedSuccessStatusRule,
    NoBodyOnGetRule,
    PathMustStartWithSlashRule,
    PathParameterConsistencyRule,
    UniqueCommandNamesRule,
    UniqueInputNamesRule,
    ValidCommandNameRule,
)


def _replace_command(
    definition: IntegrationDefinition, index: int = 0, **updates: object
) -> IntegrationDefinition:
    commands = list(definition.commands)
    commands[index] = commands[index].model_copy(update=updates)
    return definition.model_copy(update={"commands": commands})


def test_api_001_accepts_unique_command_names(
    valid_definition: IntegrationDefinition,
) -> None:
    second = valid_definition.commands[0].model_copy(update={"name": "create_board_item"})
    definition = valid_definition.model_copy(
        update={"commands": [valid_definition.commands[0], second]}
    )

    assert UniqueCommandNamesRule().evaluate(definition) == []


def test_api_001_reports_each_duplicate_after_the_first(
    valid_definition: IntegrationDefinition,
) -> None:
    command = valid_definition.commands[0]
    definition = valid_definition.model_copy(update={"commands": [command, command, command]})

    findings = UniqueCommandNamesRule().evaluate(definition)

    assert [finding.rule_id for finding in findings] == ["API-001", "API-001"]
    assert [finding.path for finding in findings] == [
        "commands[1].name",
        "commands[2].name",
    ]


@pytest.mark.parametrize("name", ["get_board_items", "get2_board3", "a"])
def test_api_002_accepts_snake_case_names(
    valid_definition: IntegrationDefinition, name: str
) -> None:
    definition = _replace_command(valid_definition, name=name)
    assert ValidCommandNameRule().evaluate(definition) == []


@pytest.mark.parametrize(
    "name", ["Get Board Items", "GetBoardItems", "get-board-items", "_get_items", "get__items"]
)
def test_api_002_rejects_non_snake_case_names(
    valid_definition: IntegrationDefinition, name: str
) -> None:
    definition = _replace_command(valid_definition, name=name)
    findings = ValidCommandNameRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "API-002"
    assert findings[0].severity.value == "error"


@pytest.mark.parametrize("path", ["/", "/v2/items", "/boards/{board_id}"])
def test_api_003_accepts_paths_starting_with_slash(
    valid_definition: IntegrationDefinition, path: str
) -> None:
    assert (
        PathMustStartWithSlashRule().evaluate(_replace_command(valid_definition, path=path)) == []
    )


def test_api_003_rejects_path_without_slash(
    valid_definition: IntegrationDefinition,
) -> None:
    findings = PathMustStartWithSlashRule().evaluate(
        _replace_command(valid_definition, path="v2/items")
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "API-003"
    assert findings[0].path == "commands[0].path"


def test_api_004_accepts_unique_input_names(
    valid_definition: IntegrationDefinition,
) -> None:
    first_input = valid_definition.commands[0].inputs[0]
    second_input = first_input.model_copy(update={"name": "workspace_id"})
    definition = _replace_command(valid_definition, inputs=[first_input, second_input])

    assert UniqueInputNamesRule().evaluate(definition) == []


def test_api_004_rejects_duplicate_input_names_per_command(
    valid_definition: IntegrationDefinition,
) -> None:
    parameter = valid_definition.commands[0].inputs[0]
    definition = _replace_command(valid_definition, inputs=[parameter, parameter])

    findings = UniqueInputNamesRule().evaluate(definition)

    assert len(findings) == 1
    assert findings[0].rule_id == "API-004"
    assert findings[0].path == "commands[0].inputs[1].name"


def test_api_005_accepts_required_path_input(
    valid_definition: IntegrationDefinition,
) -> None:
    parameter = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(update={"location": ParameterLocation.PATH, "required": True})
    )
    definition = _replace_command(
        valid_definition,
        path="/boards/{board_id}",
        inputs=[parameter],
    )

    assert PathParameterConsistencyRule().evaluate(definition) == []


@pytest.mark.parametrize(
    ("location", "required"),
    [(ParameterLocation.QUERY, True), (ParameterLocation.PATH, False)],
)
def test_api_005_rejects_wrong_location_or_optional_path_input(
    valid_definition: IntegrationDefinition,
    location: ParameterLocation,
    required: bool,
) -> None:
    parameter = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(update={"location": location, "required": required})
    )
    definition = _replace_command(
        valid_definition,
        path="/boards/{board_id}",
        inputs=[parameter],
    )

    findings = PathParameterConsistencyRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "API-005"


def test_api_005_reports_each_distinct_missing_placeholder_once(
    valid_definition: IntegrationDefinition,
) -> None:
    definition = _replace_command(
        valid_definition,
        path="/teams/{team_id}/boards/{board_id}/{board_id}",
        inputs=[],
    )

    findings = PathParameterConsistencyRule().evaluate(definition)
    assert len(findings) == 2
    assert all(finding.path == "commands[0].path" for finding in findings)


def test_api_006_accepts_post_body_and_get_query_inputs(
    valid_definition: IntegrationDefinition,
) -> None:
    rule = NoBodyOnGetRule()
    assert rule.evaluate(valid_definition) == []

    query_input = (
        valid_definition.commands[0]
        .inputs[0]
        .model_copy(update={"location": ParameterLocation.QUERY})
    )
    get_definition = _replace_command(valid_definition, method=HttpMethod.GET, inputs=[query_input])
    assert rule.evaluate(get_definition) == []


def test_api_006_warns_for_each_get_body_input(
    valid_definition: IntegrationDefinition,
) -> None:
    parameter = valid_definition.commands[0].inputs[0]
    definition = _replace_command(
        valid_definition,
        method=HttpMethod.GET,
        inputs=[parameter, parameter.model_copy(update={"name": "second_body"})],
    )

    findings = NoBodyOnGetRule().evaluate(definition)
    assert len(findings) == 2
    assert all(finding.rule_id == "API-006" for finding in findings)
    assert all(finding.severity.value == "warning" for finding in findings)


@pytest.mark.parametrize("status_code", [200, 204, 299])
def test_api_007_accepts_any_2xx_status(
    valid_definition: IntegrationDefinition, status_code: int
) -> None:
    definition = _replace_command(valid_definition, expected_status_codes=[status_code])
    assert ExpectedSuccessStatusRule().evaluate(definition) == []


@pytest.mark.parametrize("status_codes", [[199], [300], [400, 500]])
def test_api_007_requires_at_least_one_2xx_status(
    valid_definition: IntegrationDefinition, status_codes: list[int]
) -> None:
    definition = _replace_command(valid_definition, expected_status_codes=status_codes)
    findings = ExpectedSuccessStatusRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "API-007"
