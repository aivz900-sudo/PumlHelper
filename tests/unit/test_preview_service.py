import tempfile
import unittest
from pathlib import Path

from app.application.services.preview_service import DiagramPreviewService, PreviewKind
from app.infrastructure.filesystem.file_reader import FileReader
from app.infrastructure.rendering.backends import RendererBackend, RenderRequest, RenderedPreview


class DiagramPreviewServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_source(self, name: str, content: str) -> str:
        path = self.root / name
        path.write_text(content.strip(), encoding="utf-8")
        return str(path)

    def test_falls_back_to_text_when_renderer_is_unavailable(self) -> None:
        path = self._write_source(
            "diagram.puml",
            """
            @startuml
            class UserService
            @enduml
            """,
        )
        service = DiagramPreviewService(
            file_reader=FileReader(),
            backend=UnavailableBackend(),
        )

        preview = service.open_preview(path)

        self.assertEqual(preview.kind, PreviewKind.TEXT)
        self.assertIn("class UserService", preview.text)
        self.assertIn("renderer", preview.message.lower())

    def test_returns_image_preview_when_renderer_succeeds(self) -> None:
        path = self._write_source(
            "diagram.puml",
            """
            @startuml
            class UserService
            @enduml
            """,
        )
        image_path = self.root / "diagram.png"
        image_path.write_bytes(b"fake image")
        service = DiagramPreviewService(
            file_reader=FileReader(),
            backend=SuccessfulBackend(str(image_path)),
        )

        preview = service.open_preview(path)

        self.assertEqual(preview.kind, PreviewKind.IMAGE)
        self.assertEqual(preview.image_path, str(image_path))


class UnavailableBackend(RendererBackend):
    def render(self, request: RenderRequest) -> RenderedPreview:
        return RenderedPreview(
            success=False,
            image_path=None,
            error_message="Renderer is unavailable.",
        )


class SuccessfulBackend(RendererBackend):
    def __init__(self, image_path: str) -> None:
        self._image_path = image_path

    def render(self, request: RenderRequest) -> RenderedPreview:
        return RenderedPreview(
            success=True,
            image_path=self._image_path,
            error_message=None,
        )


if __name__ == "__main__":
    unittest.main()
