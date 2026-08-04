"""Schema and API-design validation rules (API-001 through API-007)."""

from __future__ import annotations

import re
from typing import Final

from app.models import (
    Category,
    Finding,
    HttpMethod,
    IntegrationDefinition,
    ParameterLocation,
    Severity,
)

from .base import ValidationRule

_COMMAND_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_PATH_PARAMETER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\{([^{}]+)\}")


class UniqueCommandNamesRule(ValidationRule):
    rule_id = "API-001"
    category = Category.API_DESIGN
    default_severity = Severity.ERROR
    title = "Unique command names"
    description = "Command names must be unique within an integration."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        for index, command in enumerate(definition.commands):
            if command.name in seen:
                findings.append(
                    self.finding(
                        path=f"commands[{index}].name",
                        message=f"Command name '{command.name}' is duplicated.",
                        recommendation="Give every command a unique name.",
                    )
                )
            else:
                seen.add(command.name)
        return findings


class ValidCommandNameRule(ValidationRule):
    rule_id = "API-002"
    category = Category.API_DESIGN
    default_severity = Severity.ERROR
    title = "Valid command name"
    description = "Command names must use snake_case."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"commands[{index}].name",
                message=f"Command name '{command.name}' is not valid snake_case.",
                recommendation="Use a lowercase snake_case name such as 'get_board_items'.",
            )
            for index, command in enumerate(definition.commands)
            if _COMMAND_NAME_PATTERN.fullmatch(command.name) is None
        ]


class PathMustStartWithSlashRule(ValidationRule):
    rule_id = "API-003"
    category = Category.API_DESIGN
    default_severity = Severity.ERROR
    title = "Path must start with slash"
    description = "Every command path must begin with '/'."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"commands[{index}].path",
                message=f"Command '{command.name}' has a path that does not start with '/'.",
                recommendation="Prefix the command path with '/'.",
            )
            for index, command in enumerate(definition.commands)
            if not command.path.startswith("/")
        ]


class UniqueInputNamesRule(ValidationRule):
    rule_id = "API-004"
    category = Category.API_DESIGN
    default_severity = Severity.ERROR
    title = "Unique input names"
    description = "Input names must be unique within each command."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings: list[Finding] = []
        for command_index, command in enumerate(definition.commands):
            seen: set[str] = set()
            for input_index, parameter in enumerate(command.inputs):
                if parameter.name in seen:
                    findings.append(
                        self.finding(
                            path=f"commands[{command_index}].inputs[{input_index}].name",
                            message=(
                                f"Input name '{parameter.name}' is duplicated in command "
                                f"'{command.name}'."
                            ),
                            recommendation="Give every input in a command a unique name.",
                        )
                    )
                else:
                    seen.add(parameter.name)
        return findings


class PathParameterConsistencyRule(ValidationRule):
    rule_id = "API-005"
    category = Category.API_DESIGN
    default_severity = Severity.ERROR
    title = "Path parameter consistency"
    description = "Every path placeholder must have a required input whose location is path."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings: list[Finding] = []
        for command_index, command in enumerate(definition.commands):
            placeholders = dict.fromkeys(_PATH_PARAMETER_PATTERN.findall(command.path))
            for placeholder in placeholders:
                matching_inputs = [
                    parameter for parameter in command.inputs if parameter.name == placeholder
                ]
                is_consistent = any(
                    parameter.location == ParameterLocation.PATH and parameter.required
                    for parameter in matching_inputs
                )
                if not is_consistent:
                    findings.append(
                        self.finding(
                            path=f"commands[{command_index}].path",
                            message=(
                                f"Path placeholder '{{{placeholder}}}' has no matching "
                                "required path input."
                            ),
                            recommendation=(
                                f"Add input '{placeholder}' with location 'path' and "
                                "required set to true."
                            ),
                        )
                    )
        return findings


class NoBodyOnGetRule(ValidationRule):
    rule_id = "API-006"
    category = Category.API_DESIGN
    default_severity = Severity.WARNING
    title = "No body on GET"
    description = "GET commands should not define body inputs."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        findings: list[Finding] = []
        for command_index, command in enumerate(definition.commands):
            if command.method != HttpMethod.GET:
                continue
            findings.extend(
                self.finding(
                    path=f"commands[{command_index}].inputs[{input_index}].location",
                    message=(
                        f"GET command '{command.name}' defines body input '{parameter.name}'."
                    ),
                    recommendation="Move the input to the path, query, or header.",
                )
                for input_index, parameter in enumerate(command.inputs)
                if parameter.location == ParameterLocation.BODY
            )
        return findings


class ExpectedSuccessStatusRule(ValidationRule):
    rule_id = "API-007"
    category = Category.API_DESIGN
    default_severity = Severity.ERROR
    title = "Expected success status"
    description = "Every command must declare at least one expected 2xx status code."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"commands[{index}].expected_status_codes",
                message=f"Command '{command.name}' has no expected 2xx status code.",
                recommendation="Add at least one expected status code from 200 through 299.",
            )
            for index, command in enumerate(definition.commands)
            if not any(200 <= status_code <= 299 for status_code in command.expected_status_codes)
        ]


SCHEMA_RULES: Final[tuple[ValidationRule, ...]] = (
    UniqueCommandNamesRule(),
    ValidCommandNameRule(),
    PathMustStartWithSlashRule(),
    UniqueInputNamesRule(),
    PathParameterConsistencyRule(),
    NoBodyOnGetRule(),
    ExpectedSuccessStatusRule(),
)

# Compatibility name matching the shorter phrasing commonly used by callers.
PathStartsWithSlashRule = PathMustStartWithSlashRule
