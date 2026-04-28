from __future__ import annotations

from pathlib import Path

from app.application.services.analysis_service import AnalysisService
from app.application.services.git_import_service import GitImportService
from app.application.services.preview_service import DiagramPreviewService
from app.infrastructure.filesystem.file_reader import FileReader
from app.infrastructure.git.repository_loader import GitRepositoryLoader
from app.presentation.main_window import MainWindow


def create_main_window() -> MainWindow:
    file_reader = FileReader()
    analysis_service = AnalysisService(file_reader=file_reader)
    preview_service = DiagramPreviewService(file_reader=file_reader)
    git_import_service = GitImportService(
        analysis_service=analysis_service,
        repository_loader=GitRepositoryLoader(
            cache_root=Path.cwd() / ".vkr_puml_git_cache",
        ),
    )
    return MainWindow(
        analysis_service=analysis_service,
        preview_service=preview_service,
        git_import_service=git_import_service,
    )
