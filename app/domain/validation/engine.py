from __future__ import annotations

from app.domain.semantics.models import ArchitectureModel
from app.domain.validation.models import ValidationContext, ValidationIssue, ValidationRule


class ValidationEngine:
    def __init__(self, rules: list[ValidationRule]) -> None:
        self._rules = rules

    def validate(self, model: ArchitectureModel) -> list[ValidationIssue]:
        context = ValidationContext(model=model)
        issues: list[ValidationIssue] = []
        for rule in self._rules:
            issues.extend(rule.validate(context))
        return issues
