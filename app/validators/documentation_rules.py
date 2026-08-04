"""Documentation validation rules (DOC-001 through DOC-005)."""

from __future__ import annotations

from typing import Final

from app.models import Category, Finding, IntegrationDefinition, Severity

from .base import ValidationRule, is_blank


class IntegrationDescriptionRule(ValidationRule):
    rule_id = "DOC-001"
    category = Category.DOCUMENTATION
    default_severity = Severity.WARNING
    title = "Integration description"
    description = "An integration should have a description."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        if is_blank(definition.description):
            return [
                self.finding(
                    path="description",
                    message="The integration has no description.",
                    recommendation="Describe the integration's purpose and capabilities.",
                )
            ]
        return []


class CommandDescriptionRule(ValidationRule):
    rule_id = "DOC-002"
    category = Category.DOCUMENTATION
    default_severity = Severity.WARNING
    title = "Command description"
    description = "Every command should have a description."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"commands[{index}].description",
                message=f"Command '{command.name}' has no description.",
                recommendation="Document what the command does and when to use it.",
            )
            for index, command in enumerate(definition.commands)
            if is_blank(command.description)
        ]


class InputDescriptionRule(ValidationRule):
    rule_id = "DOC-003"
    category = Category.DOCUMENTATION
    default_severity = Severity.WARNING
    title = "Input description"
    description = "Every command input should have a description."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"commands[{command_index}].inputs[{input_index}].description",
                message=(
                    f"Input '{parameter.name}' in command '{command.name}' has no description."
                ),
                recommendation="Describe the input's meaning, format, and constraints.",
            )
            for command_index, command in enumerate(definition.commands)
            for input_index, parameter in enumerate(command.inputs)
            if is_blank(parameter.description)
        ]


class OutputDefinitionsRule(ValidationRule):
    rule_id = "DOC-004"
    category = Category.DOCUMENTATION
    default_severity = Severity.WARNING
    title = "Output definitions"
    description = "Every command should define its outputs."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        return [
            self.finding(
                path=f"commands[{index}].outputs",
                message=f"Command '{command.name}' has no output definitions.",
                recommendation="Define the fields returned by the command.",
            )
            for index, command in enumerate(definition.commands)
            if not command.outputs
        ]


class OwnerRule(ValidationRule):
    rule_id = "DOC-005"
    category = Category.DOCUMENTATION
    default_severity = Severity.WARNING
    title = "Owner"
    description = "An integration should identify its owning team or person."

    def evaluate(self, definition: IntegrationDefinition) -> list[Finding]:
        if is_blank(definition.owner):
            return [
                self.finding(
                    path="owner",
                    message="The integration has no owner.",
                    recommendation="Set owner to the responsible team or person.",
                )
            ]
        return []


DOCUMENTATION_RULES: Final[tuple[ValidationRule, ...]] = (
    IntegrationDescriptionRule(),
    CommandDescriptionRule(),
    InputDescriptionRule(),
    OutputDefinitionsRule(),
    OwnerRule(),
)
