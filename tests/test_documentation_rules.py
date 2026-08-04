from __future__ import annotations

import pytest

from app.models import IntegrationDefinition
from app.validators.documentation_rules import (
    CommandDescriptionRule,
    InputDescriptionRule,
    IntegrationDescriptionRule,
    OutputDefinitionsRule,
    OwnerRule,
)


@pytest.mark.parametrize("description", [None, "   "])
def test_doc_001_warns_for_missing_or_blank_integration_description(
    valid_definition: IntegrationDefinition, description: str | None
) -> None:
    definition = valid_definition.model_copy(update={"description": description})
    findings = IntegrationDescriptionRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "DOC-001"


def test_doc_001_accepts_integration_description(
    valid_definition: IntegrationDefinition,
) -> None:
    assert IntegrationDescriptionRule().evaluate(valid_definition) == []


@pytest.mark.parametrize("description", [None, "  "])
def test_doc_002_warns_for_each_undocumented_command(
    valid_definition: IntegrationDefinition, description: str | None
) -> None:
    command = valid_definition.commands[0].model_copy(update={"description": description})
    definition = valid_definition.model_copy(update={"commands": [command, command]})
    findings = CommandDescriptionRule().evaluate(definition)
    assert len(findings) == 2
    assert all(finding.rule_id == "DOC-002" for finding in findings)


def test_doc_002_accepts_documented_command(
    valid_definition: IntegrationDefinition,
) -> None:
    assert CommandDescriptionRule().evaluate(valid_definition) == []


def test_doc_003_warns_for_each_undocumented_input(
    valid_definition: IntegrationDefinition,
) -> None:
    parameter = valid_definition.commands[0].inputs[0].model_copy(update={"description": None})
    command = valid_definition.commands[0].model_copy(update={"inputs": [parameter, parameter]})
    definition = valid_definition.model_copy(update={"commands": [command]})
    findings = InputDescriptionRule().evaluate(definition)
    assert len(findings) == 2
    assert all(finding.rule_id == "DOC-003" for finding in findings)


def test_doc_003_accepts_documented_input(
    valid_definition: IntegrationDefinition,
) -> None:
    assert InputDescriptionRule().evaluate(valid_definition) == []


def test_doc_004_warns_for_command_without_outputs(
    valid_definition: IntegrationDefinition,
) -> None:
    command = valid_definition.commands[0].model_copy(update={"outputs": []})
    definition = valid_definition.model_copy(update={"commands": [command]})
    findings = OutputDefinitionsRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "DOC-004"


def test_doc_004_accepts_defined_outputs(
    valid_definition: IntegrationDefinition,
) -> None:
    assert OutputDefinitionsRule().evaluate(valid_definition) == []


@pytest.mark.parametrize("owner", [None, "   "])
def test_doc_005_warns_for_missing_or_blank_owner(
    valid_definition: IntegrationDefinition, owner: str | None
) -> None:
    definition = valid_definition.model_copy(update={"owner": owner})
    findings = OwnerRule().evaluate(definition)
    assert len(findings) == 1
    assert findings[0].rule_id == "DOC-005"


def test_doc_005_accepts_owner(valid_definition: IntegrationDefinition) -> None:
    assert OwnerRule().evaluate(valid_definition) == []
