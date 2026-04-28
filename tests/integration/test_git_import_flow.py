import tempfile
import unittest
from pathlib import Path

from app.application.services.analysis_service import AnalysisService
from app.application.services.git_import_service import GitImportService
from app.infrastructure.filesystem.file_reader import FileReader
from app.infrastructure.git.repository_loader import GitRepositorySnapshot


class GitImportFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo_path = self.root / "repo-cache"
        self.analysis_service = AnalysisService(file_reader=FileReader())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_repo_file(self, relative_path: str, content: str) -> str:
        path = self.repo_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip(), encoding="utf-8")
        return str(path)

    def test_load_from_git_adds_discovered_puml_documents(self) -> None:
        class_path = self._write_repo_file(
            "docs/class.puml",
            """
            @startuml
            class UserService
            @enduml
            """,
        )
        sequence_path = self._write_repo_file(
            "docs/sequence.puml",
            """
            @startuml
            participant service:UserService
            @enduml
            """,
        )
        import_service = GitImportService(
            analysis_service=self.analysis_service,
            repository_loader=FakeRepositoryLoader(
                GitRepositorySnapshot(
                    repository_path=str(self.repo_path),
                    puml_paths=[class_path, sequence_path],
                )
            ),
        )

        result = import_service.load_from_git("https://example.com/project/repo.git")

        self.assertEqual(result.imported_paths, [class_path, sequence_path])
        self.assertEqual(result.repository_path, str(self.repo_path))
        self.assertEqual(len(self.analysis_service.project.documents), 2)

    def test_reload_removes_documents_missing_from_fresh_clone(self) -> None:
        stale_path = self._write_repo_file(
            "docs/stale.puml",
            """
            @startuml
            class Stale
            @enduml
            """,
        )
        self.analysis_service.load_files([stale_path])
        Path(stale_path).unlink()
        current_path = self._write_repo_file(
            "docs/current.puml",
            """
            @startuml
            class Current
            @enduml
            """,
        )
        import_service = GitImportService(
            analysis_service=self.analysis_service,
            repository_loader=FakeRepositoryLoader(
                GitRepositorySnapshot(
                    repository_path=str(self.repo_path),
                    puml_paths=[current_path],
                )
            ),
        )

        import_service.load_from_git("https://example.com/project/repo.git")

        document_paths = [document.path for document in self.analysis_service.project.documents]
        self.assertEqual(document_paths, [current_path])


class FakeRepositoryLoader:
    def __init__(self, snapshot: GitRepositorySnapshot) -> None:
        self.snapshot = snapshot
        self.loaded_urls: list[str] = []

    def load_repository(self, repository_url: str) -> GitRepositorySnapshot:
        self.loaded_urls.append(repository_url)
        return self.snapshot


if __name__ == "__main__":
    unittest.main()
