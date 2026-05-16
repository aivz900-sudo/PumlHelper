from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from app.domain.ast.models import (
    AttributeNode,
    ClassDiagramAst,
    ClassNode,
    MessageNode,
    OperationNode,
    ParticipantNode,
    SequenceDiagramAst,
)
from app.domain.parsing.lexer import LineLexer
from app.domain.project.models import DiagramDocument, DiagramType
from app.domain.semantics.models import (
    ClassModel,
    DocumentRef,
    OperationModel,
    SemanticFragment,
    SequenceMessage,
    SequenceParticipant,
    SequenceScenario,
)


CLASS_HEADER_RE = re.compile(r"^class\s+(?P<name>[A-Za-z_]\w*)(?:\s*\{)?$")
ATTRIBUTE_RE = re.compile(r"^[+#~-]?\s*(?P<name>[A-Za-z_]\w*)\s*:")
OPERATION_RE = re.compile(
    r"^(?P<visibility>[+#~-])?\s*(?P<abstract>\{abstract\}\s*)?"
    r"(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)"
)
PARTICIPANT_RE = re.compile(
    r"^(participant|actor|boundary|control|entity)\s+(?P<value>[A-Za-z_]\w*(?::[A-Za-z_]\w*)?)$"
)
MESSAGE_RE = re.compile(
    r"^(?P<sender>[A-Za-z_]\w*)\s*-+>\s*(?P<target>[A-Za-z_]\w*)\s*:\s*(?P<label>.+)$"
)


@dataclass(slots=True)
class ParsedDiagram:
    diagram_type: DiagramType
    ast: object
    semantic_fragment: SemanticFragment


class DiagramParser:
    diagram_type: DiagramType

    def parse(self, document: DiagramDocument) -> ParsedDiagram:
        raise NotImplementedError


class ClassDiagramParser(DiagramParser):
    diagram_type = DiagramType.CLASS

    def __init__(self) -> None:
        self._lexer = LineLexer()

    def parse(self, document: DiagramDocument) -> ParsedDiagram:
        tokens = self._lexer.tokenize(document.source_text)
        ast = ClassDiagramAst()
        index = 0

        while index < len(tokens):
            token_text = tokens[index].text
            header_match = CLASS_HEADER_RE.match(token_text)
            if not header_match:
                index += 1
                continue

            class_name = header_match.group("name")
            attributes: list[AttributeNode] = []
            operations: list[OperationNode] = []
            has_block = token_text.endswith("{")
            index += 1

            if has_block:
                while index < len(tokens) and tokens[index].text != "}":
                    member = tokens[index].text
                    operation_match = OPERATION_RE.match(member)
                    attribute_match = ATTRIBUTE_RE.match(member)
                    if operation_match:
                        operation_name = operation_match.group("name")
                        signature = f"{operation_name}({operation_match.group('params').strip()})"
                        operations.append(
                            OperationNode(
                                name=operation_name,
                                signature_repr=signature,
                                visibility=self._parse_visibility(
                                    operation_match.group("visibility")
                                ),
                                is_abstract=operation_match.group("abstract") is not None,
                            )
                        )
                    elif attribute_match:
                        attributes.append(
                            AttributeNode(
                                name=attribute_match.group("name"),
                                raw_text=member,
                            )
                        )
                    index += 1

                if index < len(tokens) and tokens[index].text == "}":
                    index += 1

            ast.classes.append(
                ClassNode(name=class_name, attributes=attributes, operations=operations)
            )

        semantic_classes: dict[str, ClassModel] = {}
        source_map: dict[str, list[DocumentRef]] = {}
        for class_node in ast.classes:
            semantic_classes[class_node.name] = ClassModel(
                name=class_node.name,
                attributes={attribute.name for attribute in class_node.attributes},
                operations={
                    operation.name: OperationModel(
                        name=operation.name,
                        signature_repr=operation.signature_repr,
                        visibility=operation.visibility,
                        is_abstract=operation.is_abstract,
                    )
                    for operation in class_node.operations
                },
                is_skeleton=not class_node.attributes and not class_node.operations,
            )
            source_map[class_node.name] = [
                DocumentRef(
                    document_path=document.path,
                    diagram_type=DiagramType.CLASS,
                    entity_name=class_node.name,
                )
            ]

        fragment = SemanticFragment(
            diagram_type=DiagramType.CLASS,
            classes=semantic_classes,
            source_map=source_map,
        )
        return ParsedDiagram(diagram_type=DiagramType.CLASS, ast=ast, semantic_fragment=fragment)

    @staticmethod
    def _parse_visibility(marker: str | None) -> str:
        return {
            "+": "public",
            "#": "protected",
            "-": "private",
        }.get(marker or "", "unknown")


class SequenceDiagramParser(DiagramParser):
    diagram_type = DiagramType.SEQUENCE

    def __init__(self) -> None:
        self._lexer = LineLexer()

    def parse(self, document: DiagramDocument) -> ParsedDiagram:
        tokens = self._lexer.tokenize(document.source_text)
        ast = SequenceDiagramAst()

        for token in tokens:
            participant_match = PARTICIPANT_RE.match(token.text)
            if participant_match:
                value = participant_match.group("value")
                alias, class_name = self._split_participant_value(value)
                ast.participants.append(ParticipantNode(alias=alias, class_name=class_name))
                continue

            message_match = MESSAGE_RE.match(token.text)
            if message_match:
                label = message_match.group("label").strip()
                operation_name = label.split("(", 1)[0].strip()
                ast.messages.append(
                    MessageNode(
                        sender=message_match.group("sender"),
                        target=message_match.group("target"),
                        operation_name=operation_name,
                        raw_label=label,
                    )
                )

        scenario = SequenceScenario(
            name=Path(document.path).stem,
            participants=[
                SequenceParticipant(name=participant.alias, class_name=participant.class_name)
                for participant in ast.participants
            ],
            messages=[
                SequenceMessage(
                    sender=message.sender,
                    target=message.target,
                    operation_name=message.operation_name,
                    raw_label=message.raw_label,
                )
                for message in ast.messages
            ],
        )

        source_map: dict[str, list[DocumentRef]] = {}
        for participant in scenario.participants:
            entity_name = participant.class_name or participant.name
            source_map.setdefault(
                entity_name,
                [],
            ).append(
                DocumentRef(
                    document_path=document.path,
                    diagram_type=DiagramType.SEQUENCE,
                    entity_name=entity_name,
                )
            )

        fragment = SemanticFragment(
            diagram_type=DiagramType.SEQUENCE,
            sequence_scenarios=[scenario],
            source_map=source_map,
        )
        return ParsedDiagram(
            diagram_type=DiagramType.SEQUENCE,
            ast=ast,
            semantic_fragment=fragment,
        )

    @staticmethod
    def _split_participant_value(value: str) -> tuple[str, str | None]:
        if ":" not in value:
            return value, None
        alias, class_name = value.split(":", 1)
        return alias.strip(), class_name.strip()
