from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.services.analysis_service import AnalysisService
from app.application.services.preview_service import DiagramPreviewService
from app.domain.project.models import DiagramType
from app.presentation.dialogs.preview_dialog import DiagramPreviewDialog


class MainWindow(QMainWindow):
    def __init__(
        self,
        analysis_service: AnalysisService,
        preview_service: DiagramPreviewService,
    ) -> None:
        super().__init__()
        self._analysis_service = analysis_service
        self._preview_service = preview_service
        self._preview_dialog: DiagramPreviewDialog | None = None
        self.setWindowTitle("PlantUML Integrity Analyzer")
        self.resize(1100, 700)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.addLayout(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        self._documents_table = QTableWidget(0, 4)
        self._documents_table.setHorizontalHeaderLabels(["Файл", "Путь", "Тип", "Статус"])
        self._documents_table.horizontalHeader().setStretchLastSection(True)
        self._documents_table.verticalHeader().setVisible(False)
        self._documents_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._documents_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Отчёт"))
        self._report_output = QTextEdit()
        self._report_output.setReadOnly(True)
        right_layout.addWidget(self._report_output)

        splitter.addWidget(self._documents_table)
        splitter.addWidget(right_panel)
        splitter.setSizes([650, 450])

        self.setStatusBar(QStatusBar())
        self._set_status("Готово.")

    def _build_toolbar(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        load_button = QPushButton("Загрузить")
        load_button.clicked.connect(self._load_files)
        layout.addWidget(load_button)

        remove_button = QPushButton("Удалить")
        remove_button.clicked.connect(self._remove_selected)
        layout.addWidget(remove_button)

        preview_button = QPushButton("Просмотреть")
        preview_button.clicked.connect(self._open_preview)
        layout.addWidget(preview_button)

        analyze_button = QPushButton("Анализировать")
        analyze_button.clicked.connect(self._run_analysis)
        layout.addWidget(analyze_button)

        save_button = QPushButton("Сохранить отчёт")
        save_button.clicked.connect(self._save_report)
        layout.addWidget(save_button)

        layout.addStretch(1)
        return layout

    def _load_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите PlantUML файлы",
            "",
            "PlantUML (*.puml);;All files (*.*)",
        )
        if not paths:
            return

        self._analysis_service.load_files(paths)
        self._refresh_table()
        self._set_status(f"Загружено файлов: {len(paths)}")

    def _remove_selected(self) -> None:
        selection_model = self._documents_table.selectionModel()
        if selection_model is None:
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return

        for model_index in reversed(selected_rows):
            row = model_index.row()
            path_item = self._documents_table.item(row, 1)
            if path_item is not None:
                self._analysis_service.remove_file(path_item.text())

        self._refresh_table()
        self._set_status("Выбранные файлы удалены.")

    def _run_analysis(self) -> None:
        try:
            result = self._analysis_service.analyze()
        except Exception as error:  # pragma: no cover - UI guard
            QMessageBox.critical(self, "Ошибка анализа", str(error))
            self._set_status("Анализ завершился ошибкой.")
            return

        self._report_output.setPlainText(result.report.to_text())
        self._set_status(
            f"Анализ завершён: ошибок {len(result.report.errors)}, "
            f"предупреждений {len(result.report.warnings)}."
        )

    def _save_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт",
            str(Path.cwd() / "analysis-report.md"),
            "Markdown (*.md);;Text (*.txt)",
        )
        if not path:
            return

        try:
            self._analysis_service.save_report(path)
        except Exception as error:  # pragma: no cover - UI guard
            QMessageBox.critical(self, "Ошибка сохранения", str(error))
            return

        self._set_status(f"Отчёт сохранён: {path}")

    def _open_preview(self) -> None:
        selection_model = self._documents_table.selectionModel()
        if selection_model is None:
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Просмотр", "Сначала выберите файл в таблице.")
            return

        row = selected_rows[0].row()
        path_item = self._documents_table.item(row, 1)
        if path_item is None:
            return

        try:
            preview = self._preview_service.open_preview(path_item.text())
        except Exception as error:  # pragma: no cover - UI guard
            QMessageBox.critical(self, "Ошибка просмотра", str(error))
            return

        self._preview_dialog = DiagramPreviewDialog(preview, self)
        self._preview_dialog.show()
        self._preview_dialog.raise_()
        self._preview_dialog.activateWindow()

    def _refresh_table(self) -> None:
        documents = self._analysis_service.project.documents
        self._documents_table.clearContents()
        self._documents_table.setRowCount(len(documents))

        for row, document in enumerate(documents):
            self._documents_table.setItem(row, 0, QTableWidgetItem(document.file_name))
            self._documents_table.setItem(row, 1, QTableWidgetItem(document.path))
            self._documents_table.setItem(row, 3, QTableWidgetItem(document.status.value))

            combo_box = QComboBox()
            combo_box.addItem("Не выбран", None)
            for diagram_type in DiagramType.ordered():
                combo_box.addItem(diagram_type.value, diagram_type.value)

            combo_box.blockSignals(True)
            if document.diagram_type is not None:
                combo_box.setCurrentText(self._coerce_diagram_type(document.diagram_type).value)
            combo_box.blockSignals(False)

            combo_box.currentIndexChanged.connect(
                lambda _index, doc_path=document.path, widget=combo_box: self._on_type_changed(
                    doc_path,
                    widget,
                )
            )
            self._documents_table.setCellWidget(row, 2, combo_box)

    def _on_type_changed(self, path: str, combo_box: QComboBox) -> None:
        diagram_type = self._coerce_diagram_type(combo_box.currentData())
        if diagram_type is None:
            document = self._analysis_service.project.find_document(path)
            if document is not None:
                document.diagram_type = None
        else:
            self._analysis_service.assign_type(path, diagram_type)

        self._update_row_status(path)

    def _update_row_status(self, path: str) -> None:
        document = self._analysis_service.project.find_document(path)
        if document is None:
            return

        for row in range(self._documents_table.rowCount()):
            path_item = self._documents_table.item(row, 1)
            if path_item is None or path_item.text() != path:
                continue

            self._documents_table.setItem(row, 3, QTableWidgetItem(document.status.value))
            return

    def _set_status(self, message: str) -> None:
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage(message)

    @staticmethod
    def _coerce_diagram_type(value: Any) -> DiagramType | None:
        if value is None or value == "":
            return None
        if isinstance(value, DiagramType):
            return value
        return DiagramType(value)
