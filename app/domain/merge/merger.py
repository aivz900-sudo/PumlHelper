from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.domain.semantics.models import ArchitectureModel, ClassModel, DocumentRef, SemanticFragment


class MergeSeverity(str, Enum):
    WARNING = "warning"
    CONFLICT = "conflict"


@dataclass(slots=True)
class MergeIssue:
    severity: MergeSeverity
    class_name: str
    message: str
    related_documents: list[str] = field(default_factory=list)


class ModelMerger:
    def merge(self, fragments: list[SemanticFragment]) -> ArchitectureModel:
        model = ArchitectureModel()

        for fragment in fragments:
            model.sequence_scenarios.extend(fragment.sequence_scenarios)

            for entity_name, refs in fragment.source_map.items():
                model.source_map.setdefault(entity_name, []).extend(refs)

            for class_name, incoming_class in fragment.classes.items():
                existing_class = model.classes.get(class_name)
                if existing_class is None:
                    model.classes[class_name] = ClassModel(
                        name=incoming_class.name,
                        attributes=set(incoming_class.attributes),
                        operations=dict(incoming_class.operations),
                        is_skeleton=incoming_class.is_skeleton,
                    )
                    continue

                self._merge_class_into_model(
                    model=model,
                    existing_class=existing_class,
                    incoming_class=incoming_class,
                    class_name=class_name,
                )

        model.operations_index = {
            class_name: set(class_model.operations.keys())
            for class_name, class_model in model.classes.items()
        }
        return model

    def _merge_class_into_model(
        self,
        model: ArchitectureModel,
        existing_class: ClassModel,
        incoming_class: ClassModel,
        class_name: str,
    ) -> None:
        had_new_data = False
        had_conflict = False

        new_attributes = incoming_class.attributes - existing_class.attributes
        if new_attributes:
            existing_class.attributes.update(new_attributes)
            had_new_data = True

        for operation_name, incoming_operation in incoming_class.operations.items():
            existing_operation = existing_class.operations.get(operation_name)
            if existing_operation is None:
                existing_class.operations[operation_name] = incoming_operation
                had_new_data = True
                continue

            if existing_operation.signature_repr != incoming_operation.signature_repr:
                model.merge_issues.append(
                    MergeIssue(
                        severity=MergeSeverity.CONFLICT,
                        class_name=class_name,
                        message=(
                            f"Конфликт сигнатуры метода '{operation_name}' для класса '{class_name}'."
                        ),
                        related_documents=self._related_documents(model.source_map.get(class_name, [])),
                    )
                )
                had_conflict = True

        if existing_class.is_skeleton and (
            incoming_class.attributes or incoming_class.operations
        ):
            existing_class.is_skeleton = False
            had_new_data = True

        if incoming_class.is_skeleton and not had_new_data and not had_conflict:
            return

        if not had_new_data and not had_conflict:
            model.merge_issues.append(
                MergeIssue(
                    severity=MergeSeverity.WARNING,
                    class_name=class_name,
                    message=f"Повторное объявление класса '{class_name}' без новых данных.",
                    related_documents=self._related_documents(model.source_map.get(class_name, [])),
                )
            )

    @staticmethod
    def _related_documents(refs: list[DocumentRef]) -> list[str]:
        return sorted({ref.document_path for ref in refs})
