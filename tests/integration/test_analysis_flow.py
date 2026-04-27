import tempfile
import unittest
from pathlib import Path

from app.application.services.analysis_service import AnalysisService
from app.domain.project.models import DiagramType
from app.infrastructure.filesystem.file_reader import FileReader


class AnalysisFlowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.service = AnalysisService(file_reader=FileReader())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_file(self, name: str, content: str) -> str:
        path = self.root / name
        path.write_text(content.strip(), encoding="utf-8")
        return str(path)

    def test_multiple_files_with_assigned_types_build_unified_model(self) -> None:
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

        self.service.load_files([class_path, sequence_path])
        self.service.assign_type(class_path, DiagramType.CLASS)
        self.service.assign_type(sequence_path, DiagramType.SEQUENCE)

        result = self.service.analyze()

        self.assertIn("UserService", result.model.classes)
        self.assertEqual(len(result.model.sequence_scenarios), 1)

    def test_unknown_class_in_sequence_is_reported(self) -> None:
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
            participant service:UnknownService
            participant client:Client
            client -> service: login()
            @enduml
            """,
        )

        self.service.load_files([class_path, sequence_path])
        self.service.assign_type(class_path, DiagramType.CLASS)
        self.service.assign_type(sequence_path, DiagramType.SEQUENCE)

        result = self.service.analyze()

        self.assertTrue(any(issue.entity_name == "UnknownService" for issue in result.report.errors))

    def test_unknown_operation_in_sequence_is_reported(self) -> None:
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
            client -> service: logout()
            @enduml
            """,
        )

        self.service.load_files([class_path, sequence_path])
        self.service.assign_type(class_path, DiagramType.CLASS)
        self.service.assign_type(sequence_path, DiagramType.SEQUENCE)

        result = self.service.analyze()

        self.assertTrue(any(issue.entity_name == "logout" for issue in result.report.errors))


if __name__ == "__main__":
    unittest.main()
