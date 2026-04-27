from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QTextEdit, QVBoxLayout

from app.application.services.preview_service import DiagramPreview, PreviewKind


class DiagramPreviewDialog(QDialog):
    def __init__(self, preview: DiagramPreview, parent=None) -> None:
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle(f"Просмотр: {Path(preview.source_path).name}")
        self.resize(900, 650)

        layout = QVBoxLayout(self)

        self.message_label = QLabel(preview.message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.image_label = QLabel()
        self.image_label.setScaledContents(False)
        self.image_label.hide()
        layout.addWidget(self.image_label)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.hide()
        layout.addWidget(self.text_view)

        if preview.kind is PreviewKind.IMAGE and preview.image_path:
            pixmap = QPixmap(preview.image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap)
                self.image_label.show()
            else:
                self.text_view.setPlainText(preview.text)
                self.text_view.show()
        else:
            self.text_view.setPlainText(preview.text)
            self.text_view.show()
