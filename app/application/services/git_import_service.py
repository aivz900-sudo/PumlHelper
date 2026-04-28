from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.services.analysis_service import AnalysisService
from app.infrastructure.git.repository_loader import GitRepositoryLoader


@dataclass(slots=True)
class GitImportResult:
    imported_paths: list[str]
    repository_path: str


class GitImportService:
    def __init__(
        self,
        analysis_service: AnalysisService,
        repository_loader: GitRepositoryLoader,
    ) -> None:
        self._analysis_service = analysis_service
        self._repository_loader = repository_loader

    def load_from_git(self, repository_url: str) -> GitImportResult:
        snapshot = self._repository_loader.load_repository(repository_url)
        self._remove_existing_repository_documents(snapshot.repository_path)
        self._analysis_service.load_files(snapshot.puml_paths)
        return GitImportResult(
            imported_paths=snapshot.puml_paths,
            repository_path=snapshot.repository_path,
        )

    def _remove_existing_repository_documents(self, repository_path: str) -> None:
        repository_root = Path(repository_path).resolve(strict=False)
        for document in list(self._analysis_service.project.documents):
            document_path = Path(document.path).resolve(strict=False)
            if document_path.is_relative_to(repository_root):
                self._analysis_service.remove_file(document.path)
