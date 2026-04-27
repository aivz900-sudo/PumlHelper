from __future__ import annotations

from app.domain.reporting.models import ValidationReport


class ReportExporter:
    def save(self, report: ValidationReport, path: str) -> None:
        with open(path, "w", encoding="utf-8") as file:
            file.write(report.to_text())
