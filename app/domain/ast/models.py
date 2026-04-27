from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AttributeNode:
    name: str
    raw_text: str


@dataclass(slots=True)
class OperationNode:
    name: str
    signature_repr: str


@dataclass(slots=True)
class ClassNode:
    name: str
    attributes: list[AttributeNode] = field(default_factory=list)
    operations: list[OperationNode] = field(default_factory=list)


@dataclass(slots=True)
class ClassDiagramAst:
    classes: list[ClassNode] = field(default_factory=list)


@dataclass(slots=True)
class ParticipantNode:
    alias: str
    class_name: str | None = None


@dataclass(slots=True)
class MessageNode:
    sender: str
    target: str
    operation_name: str
    raw_label: str


@dataclass(slots=True)
class SequenceDiagramAst:
    participants: list[ParticipantNode] = field(default_factory=list)
    messages: list[MessageNode] = field(default_factory=list)
