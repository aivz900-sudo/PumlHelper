from __future__ import annotations

from app.domain.validation.models import (
    ValidationContext,
    ValidationIssue,
    ValidationRule,
    ValidationSeverity,
)


class MissingClassRule(ValidationRule):
    rule_id = "missing-class"
    title = "Sequence participant must resolve to class"

    def validate(self, context: ValidationContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for scenario in context.model.sequence_scenarios:
            for participant in scenario.participants:
                expected_class = participant.class_name or participant.name
                if expected_class not in context.model.classes:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            rule_id=self.rule_id,
                            message=(
                                f"Участник '{participant.name}' ссылается на отсутствующий класс "
                                f"'{expected_class}'."
                            ),
                            entity_name=expected_class,
                            document_paths=[
                                ref.document_path
                                for ref in context.model.source_map.get(expected_class, [])
                            ],
                        )
                    )
        return issues


class MissingOperationRule(ValidationRule):
    rule_id = "missing-operation"
    title = "Sequence message must resolve to class operation"

    def validate(self, context: ValidationContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for scenario in context.model.sequence_scenarios:
            participants = {participant.name: participant for participant in scenario.participants}
            for message in scenario.messages:
                target = participants.get(message.target)
                if target is None:
                    continue

                target_class = target.class_name
                if target_class is None and target.name in context.model.classes:
                    target_class = target.name

                if target_class is None or target_class not in context.model.classes:
                    continue

                if message.operation_name not in context.model.operations_index.get(target_class, set()):
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            rule_id=self.rule_id,
                            message=(
                                f"Операция '{message.operation_name}' отсутствует в классе "
                                f"'{target_class}'."
                            ),
                            entity_name=message.operation_name,
                            document_paths=[
                                ref.document_path
                                for ref in context.model.source_map.get(target_class, [])
                            ],
                        )
                    )
        return issues
