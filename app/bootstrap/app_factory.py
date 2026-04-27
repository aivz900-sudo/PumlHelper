from __future__ import annotations

from app.application.services.analysis_service import AnalysisService
from app.application.services.preview_service import DiagramPreviewService
from app.infrastructure.filesystem.file_reader import FileReader
from app.presentation.main_window import MainWindow


def create_main_window() -> MainWindow:
    file_reader = FileReader()
    analysis_service = AnalysisService(file_reader=file_reader)
    preview_service = DiagramPreviewService(file_reader=file_reader)
    return MainWindow(
        analysis_service=analysis_service,
        preview_service=preview_service,
    )
