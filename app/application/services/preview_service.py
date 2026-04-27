from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.infrastructure.filesystem.file_reader import FileReader
from app.infrastructure.rendering.backends import (
    PlantUMLRendererBackend,
    RenderRequest,
    RendererBackend,
)


class PreviewKind(str, Enum):
    IMAGE = "image"
    TEXT = "text"


@dataclass(slots=True)
class DiagramPreview:
    kind: PreviewKind
    source_path: str
    image_path: str | None
    text: str
    message: str


class DiagramPreviewService:
    def __init__(
        self,
        file_reader: FileReader,
        backend: RendererBackend | None = None,
    ) -> None:
        self._file_reader = file_reader
        self._backend = backend or PlantUMLRendererBackend()

    def open_preview(self, source_path: str) -> DiagramPreview:
        source_text = self._file_reader.read_text(source_path)
        rendered = self._backend.render(
            RenderRequest(
                source_path=source_path,
                source_text=source_text,
            )
        )
        if rendered.success and rendered.image_path:
            return DiagramPreview(
                kind=PreviewKind.IMAGE,
                source_path=source_path,
                image_path=rendered.image_path,
                text=source_text,
                message="Диаграмма успешно отрендерена.",
            )

        return DiagramPreview(
            kind=PreviewKind.TEXT,
            source_path=source_path,
            image_path=None,
            text=source_text,
            message=(
                "Preview renderer is unavailable. "
                f"Showing source text instead. Details: {rendered.error_message or 'unknown'}"
            ),
        )
