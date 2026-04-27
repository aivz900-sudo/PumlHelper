from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.domain.semantics.models import ArchitectureModel


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(slots=True)
class ValidationIssue:
    severity: ValidationSeverity
    rule_id: str
    message: str
    entity_name: str
    document_paths: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValidationContext:
    model: ArchitectureModel


class ValidationRule:
    rule_id: str
    title: str

    def validate(self, context: ValidationContext) -> list[ValidationIssue]:
        raise NotImplementedError
