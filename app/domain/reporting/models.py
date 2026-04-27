from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.merge.merger import MergeIssue, MergeSeverity
from app.domain.semantics.models import ArchitectureModel
from app.domain.validation.models import ValidationIssue, ValidationSeverity


@dataclass(slots=True)
class ValidationReport:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    info: list[ValidationIssue] = field(default_factory=list)
    merge_issues: list[MergeIssue] = field(default_factory=list)
    found_entities: list[str] = field(default_factory=list)

    @classmethod
    def from_results(
        cls,
        model: ArchitectureModel,
        issues: list[ValidationIssue],
    ) -> "ValidationReport":
        report = cls(
            merge_issues=model.merge_issues.copy(),
            found_entities=sorted(model.classes.keys()),
        )
        for issue in issues:
            if issue.severity is ValidationSeverity.ERROR:
                report.errors.append(issue)
            elif issue.severity is ValidationSeverity.WARNING:
                report.warnings.append(issue)
            else:
                report.info.append(issue)
        return report

    def to_text(self) -> str:
        lines = [
            "Отчёт анализа PlantUML",
            "",
            f"Классов: {len(self.found_entities)}",
            f"Ошибок: {len(self.errors)}",
            f"Предупреждений: {len(self.warnings)}",
            f"Merge issues: {len(self.merge_issues)}",
            "",
        ]
        if self.found_entities:
            lines.append("Найденные сущности:")
            lines.extend(f"- {entity}" for entity in self.found_entities)
            lines.append("")
        if self.errors:
            lines.append("Ошибки:")
            lines.extend(f"- [{issue.rule_id}] {issue.message}" for issue in self.errors)
            lines.append("")
        if self.warnings:
            lines.append("Предупреждения:")
            lines.extend(f"- [{issue.rule_id}] {issue.message}" for issue in self.warnings)
            lines.append("")
        if self.merge_issues:
            lines.append("Merge issues:")
            for issue in self.merge_issues:
                lines.append(f"- [{issue.severity}] {issue.message}")
        return "\n".join(lines).strip() + "\n"
