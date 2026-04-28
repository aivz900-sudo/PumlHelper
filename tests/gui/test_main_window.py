import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox

from app.application.services.analysis_service import AnalysisService
from app.application.services.git_import_service import GitImportService
from app.application.services.preview_service import DiagramPreviewService, PreviewKind
from app.domain.project.models import DiagramType
from app.infrastructure.filesystem.file_reader import FileReader
from app.infrastructure.git.repository_loader import GitRepositorySnapshot
from app.infrastructure.rendering.backends import RendererBackend, RenderRequest, RenderedPreview
from app.presentation.main_window import MainWindow


class MainWindowRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.service = AnalysisService(file_reader=FileReader())
        self.preview_service = DiagramPreviewService(
            file_reader=FileReader(),
            backend=UnavailableBackend(),
        )
        self.git_import_service = GitImportService(
            analysis_service=self.service,
            repository_loader=FakeRepositoryLoader(
                GitRepositorySnapshot(repository_path=str(self.root), puml_paths=[])
            ),
        )
        self.window = MainWindow(self.service, self.preview_service, self.git_import_service)

    def tearDown(self) -> None:
        self.window.close()
        self.temp_dir.cleanup()

    def _write_file(self, name: str, content: str) -> str:
        path = self.root / name
        path.write_text(content.strip(), encoding="utf-8")
        return str(path)

    def test_incremental_file_addition_and_type_assignment_keep_two_ready_rows(self) -> None:
        class_path = self._write_file(
            "class.puml",
            """
            @startuml
            class UserService {
              +login()
            }
            @enduml
            """,
        )
        sequence_path = self._write_file(
            "sequence.puml",
            """
            @startuml
            participant service:UserService
            participant client:Client
            client -> service: login()
            @enduml
            """,
        )

        self.service.load_files([class_path])
        self.window._refresh_table()
        self.service.load_files([sequence_path])
        self.window._refresh_table()

        self.assertEqual(self.window._documents_table.rowCount(), 2)

        first_combo = self.window._documents_table.cellWidget(0, 2)
        self.assertIsInstance(first_combo, QComboBox)
        first_combo.setCurrentText(DiagramType.CLASS.value)
        QApplication.processEvents()

        second_combo = self.window._documents_table.cellWidget(1, 2)
        self.assertIsInstance(second_combo, QComboBox)
        second_combo.setCurrentText(DiagramType.SEQUENCE.value)
        QApplication.processEvents()

        self.assertEqual(self.window._documents_table.rowCount(), 2)
        self.assertEqual(self.window._documents_table.item(0, 3).text(), "ready")
        self.assertEqual(self.window._documents_table.item(1, 3).text(), "ready")
        self.assertNotEqual(self.window._documents_table.item(0, 0).text(), "")
        self.assertNotEqual(self.window._documents_table.item(1, 0).text(), "")

    def test_open_preview_uses_text_fallback_when_renderer_unavailable(self) -> None:
        path = self._write_file(
            "class.puml",
            """
            @startuml
            class UserService
            @enduml
            """,
        )

        self.service.load_files([path])
        self.window._refresh_table()
        self.window._documents_table.selectRow(0)

        self.window._open_preview()
        QApplication.processEvents()

        dialog = self.window._preview_dialog
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.preview.kind, PreviewKind.TEXT)
        self.assertIn("UserService", dialog.preview.text)

    def test_load_from_git_refreshes_table_and_allows_removing_imported_files(self) -> None:
        class_path = self._write_file(
            "class.puml",
            """
            @startuml
            class UserService
            @enduml
            """,
        )
        extra_path = self._write_file(
            "extra.puml",
            """
            @startuml
            class Extra
            @enduml
            """,
        )
        self.git_import_service = GitImportService(
            analysis_service=self.service,
            repository_loader=FakeRepositoryLoader(
                GitRepositorySnapshot(
                    repository_path=str(self.root),
                    puml_paths=[class_path, extra_path],
                )
            ),
        )
        self.window.close()
        self.window = MainWindow(self.service, self.preview_service, self.git_import_service)

        with patch(
            "app.presentation.main_window.QInputDialog.getText",
            return_value=("https://example.com/project/repo.git", True),
        ):
            self.window._load_from_git()

        self.assertEqual(self.window._documents_table.rowCount(), 2)

        self.window._documents_table.selectRow(1)
        self.window._remove_selected()

        self.assertEqual(self.window._documents_table.rowCount(), 1)
        self.assertEqual(self.window._documents_table.item(0, 0).text(), "class.puml")


class UnavailableBackend(RendererBackend):
    def render(self, request: RenderRequest) -> RenderedPreview:
        return RenderedPreview(
            success=False,
            image_path=None,
            error_message="Renderer is unavailable.",
        )


class FakeRepositoryLoader:
    def __init__(self, snapshot: GitRepositorySnapshot) -> None:
        self.snapshot = snapshot

    def load_repository(self, repository_url: str) -> GitRepositorySnapshot:
        return self.snapshot


if __name__ == "__main__":
    unittest.main()
