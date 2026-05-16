from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.project.models import DiagramType


@dataclass(slots=True, frozen=True)
class DocumentRef:
    document_path: str
    diagram_type: DiagramType
    entity_name: str


@dataclass(slots=True)
class OperationModel:
    name: str
    signature_repr: str
    visibility: str = "unknown"
    is_abstract: bool = False


@dataclass(slots=True)
class ClassModel:
    name: str
    attributes: set[str] = field(default_factory=set)
    operations: dict[str, OperationModel] = field(default_factory=dict)
    is_skeleton: bool = False


@dataclass(slots=True)
class SequenceParticipant:
    name: str
    class_name: str | None = None


@dataclass(slots=True)
class SequenceMessage:
    sender: str
    target: str
    operation_name: str
    raw_label: str


@dataclass(slots=True)
class SequenceScenario:
    name: str
    participants: list[SequenceParticipant] = field(default_factory=list)
    messages: list[SequenceMessage] = field(default_factory=list)


@dataclass(slots=True)
class SemanticFragment:
    diagram_type: DiagramType
    classes: dict[str, ClassModel] = field(default_factory=dict)
    sequence_scenarios: list[SequenceScenario] = field(default_factory=list)
    source_map: dict[str, list[DocumentRef]] = field(default_factory=dict)


@dataclass(slots=True)
class ArchitectureModel:
    classes: dict[str, ClassModel] = field(default_factory=dict)
    operations_index: dict[str, set[str]] = field(default_factory=dict)
    sequence_scenarios: list[SequenceScenario] = field(default_factory=list)
    source_map: dict[str, list[DocumentRef]] = field(default_factory=dict)
    merge_issues: list[object] = field(default_factory=list)
