from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Token:
    line_number: int
    text: str


class LineLexer:
    def tokenize(self, source_text: str) -> list[Token]:
        tokens: list[Token] = []
        for index, raw_line in enumerate(source_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("'"):
                continue
            if line in {"@startuml", "@enduml"}:
                continue
            tokens.append(Token(line_number=index, text=line))
        return tokens
