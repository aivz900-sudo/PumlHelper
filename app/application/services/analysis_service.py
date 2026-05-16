from __future__ import annotations

from dataclasses import dataclass

from app.domain.merge.merger import ModelMerger
from app.domain.project.models import DiagramDocument, DiagramType, Project
from app.domain.reporting.models import ValidationReport
from app.domain.validation.engine import ValidationEngine
from app.domain.validation.rules import (
    AbstractOperationCallRule,
    MissingClassRule,
    MissingOperationRule,
    OperationVisibilityRule,
)
from app.infrastructure.export.report_exporter import ReportExporter
from app.infrastructure.filesystem.file_reader import FileReader
from app.domain.parsing.parsers import ClassDiagramParser, DiagramParser, SequenceDiagramParser


@dataclass(slots=True)
class AnalysisResult:
    model: object
    report: ValidationReport


class AnalysisService:
    def __init__(
        self,
        file_reader: FileReader,
        report_exporter: ReportExporter | None = None,
    ) -> None:
        self._file_reader = file_reader
        self._report_exporter = report_exporter or ReportExporter()
        self._project = Project()
        self._parsers: dict[DiagramType, DiagramParser] = {
            DiagramType.CLASS: ClassDiagramParser(),
            DiagramType.SEQUENCE: SequenceDiagramParser(),
        }
        self._merger = ModelMerger()
        self._validation_engine = ValidationEngine(
            [
                MissingClassRule(),
                MissingOperationRule(),
                AbstractOperationCallRule(),
                OperationVisibilityRule(),
            ]
        )

    @property
    def project(self) -> Project:
        return self._project

    def load_files(self, paths: list[str]) -> None:
        for path in paths:
            source_text = self._file_reader.read_text(path)
            existing = self._project.find_document(path)
            diagram_type = existing.diagram_type if existing else None
            self._project.upsert_document(
                DiagramDocument(path=path, source_text=source_text, diagram_type=diagram_type)
            )

    def remove_file(self, path: str) -> None:
        self._project.remove_document(path)

    def assign_type(self, path: str, diagram_type: DiagramType) -> None:
        document = self._project.find_document(path)
        if document is None:
            raise ValueError(f"Документ не найден: {path}")
        document.diagram_type = diagram_type

    def analyze(self) -> AnalysisResult:
        fragments = []
        for document in self._project.ready_documents():
            parser = self._parsers.get(document.diagram_type)
            if parser is None:
                continue
            parsed = parser.parse(document)
            fragments.append(parsed.semantic_fragment)

        model = self._merger.merge(fragments)
        issues = self._validation_engine.validate(model)
        report = ValidationReport.from_results(model=model, issues=issues)
        self._project.last_model = model
        self._project.last_report = report
        return AnalysisResult(model=model, report=report)

    def save_report(self, path: str) -> None:
        if not isinstance(self._project.last_report, ValidationReport):
            raise ValueError("Нет отчёта для сохранения.")
        self._report_exporter.save(self._project.last_report, path)
