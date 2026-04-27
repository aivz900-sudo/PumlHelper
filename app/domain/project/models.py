from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DiagramType(str, Enum):
    SEQUENCE = "Диаграмма последовательности"
    USE_CASE = "Диаграмма прецедентов"
    CLASS = "Диаграмма классов"
    OBJECT = "Диаграмма объектов"
    ACTIVITY = "Диаграмма активности"
    COMPONENT = "Диаграмма компонентов"
    DEPLOYMENT = "Диаграмма развёртывания"
    STATE = "Диаграмма состояний"
    TIMING = "Диаграмма синхронизации"

    @classmethod
    def ordered(cls) -> list["DiagramType"]:
        return [
            cls.SEQUENCE,
            cls.USE_CASE,
            cls.CLASS,
            cls.OBJECT,
            cls.ACTIVITY,
            cls.COMPONENT,
            cls.DEPLOYMENT,
            cls.STATE,
            cls.TIMING,
        ]


class DocumentStatus(str, Enum):
    INCOMPLETE = "incomplete"
    READY = "ready"
    ERROR = "error"


@dataclass(slots=True)
class DiagramDocument:
    path: str
    source_text: str = ""
    diagram_type: DiagramType | None = None
    error_message: str | None = None

    @property
    def file_name(self) -> str:
        return Path(self.path).name

    @property
    def status(self) -> DocumentStatus:
        if self.error_message:
            return DocumentStatus.ERROR
        if self.diagram_type is None:
            return DocumentStatus.INCOMPLETE
        return DocumentStatus.READY

    @property
    def ready_for_analysis(self) -> bool:
        return self.status is DocumentStatus.READY


@dataclass(slots=True)
class Project:
    documents: list[DiagramDocument] = field(default_factory=list)
    last_model: object | None = None
    last_report: object | None = None

    def upsert_document(self, document: DiagramDocument) -> None:
        existing = self.find_document(document.path)
        if existing is None:
            self.documents.append(document)
            return
        existing.source_text = document.source_text
        existing.diagram_type = document.diagram_type
        existing.error_message = document.error_message

    def find_document(self, path: str) -> DiagramDocument | None:
        for document in self.documents:
            if document.path == path:
                return document
        return None

    def remove_document(self, path: str) -> None:
        self.documents = [document for document in self.documents if document.path != path]

    def ready_documents(self) -> list[DiagramDocument]:
        return [document for document in self.documents if document.ready_for_analysis]
