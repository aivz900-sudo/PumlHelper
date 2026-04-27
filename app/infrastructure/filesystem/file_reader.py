from __future__ import annotations


class FileReader:
    def read_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
