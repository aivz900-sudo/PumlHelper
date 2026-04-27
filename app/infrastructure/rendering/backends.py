from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


@dataclass(slots=True)
class RenderRequest:
    source_path: str
    source_text: str


@dataclass(slots=True)
class RenderedPreview:
    success: bool
    image_path: str | None
    error_message: str | None


class RendererBackend:
    def render(self, request: RenderRequest) -> RenderedPreview:
        raise NotImplementedError


class PlantUMLRendererBackend(RendererBackend):
    def __init__(self, plantuml_jar: str | None = None) -> None:
        self._plantuml_jar = plantuml_jar

    def render(self, request: RenderRequest) -> RenderedPreview:
        plantuml_exe = self._find_plantuml_executable()
        dot_exe = self._find_dot_executable()
        java_exe = self._find_java_executable()
        plantuml_jar = self._plantuml_jar or self._find_default_jar()

        if plantuml_exe is None and (java_exe is None or plantuml_jar is None):
            return RenderedPreview(
                success=False,
                image_path=None,
                error_message="PlantUML renderer is unavailable.",
            )

        output_dir = Path(tempfile.mkdtemp(prefix="plantuml-preview-"))
        source_path = output_dir / Path(request.source_path).name
        source_path.write_text(request.source_text, encoding="utf-8")
        image_path = output_dir / f"{source_path.stem}.png"

        if plantuml_exe is not None:
            command = [plantuml_exe, "-tpng", "-o", str(output_dir), str(source_path)]
        else:
            command = [
                java_exe,
                "-jar",
                str(plantuml_jar),
                "-tpng",
                "-o",
                str(output_dir),
                str(source_path),
            ]

        environment = os.environ.copy()
        if dot_exe is not None:
            dot_dir = str(Path(dot_exe).parent)
            environment["PATH"] = (
                f"{dot_dir}{os.pathsep}{environment.get('PATH', '')}"
                if environment.get("PATH")
                else dot_dir
            )

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        if completed.returncode != 0 or not image_path.exists():
            error_output = completed.stderr.strip() or completed.stdout.strip() or "Unknown render error."
            return RenderedPreview(
                success=False,
                image_path=None,
                error_message=error_output,
            )

        return RenderedPreview(
            success=True,
            image_path=str(image_path),
            error_message=None,
        )

    @staticmethod
    def _find_default_jar() -> str | None:
        cwd = Path.cwd()
        candidates = (
            list(cwd.glob("plantuml*.jar"))
            + list((cwd / "tools").glob("plantuml*.jar"))
            + list((cwd / "tools" / "plantuml").glob("plantuml*.jar"))
        )
        if not candidates:
            return None
        return str(sorted(candidates)[0])

    @staticmethod
    def _find_plantuml_executable() -> str | None:
        candidates = [
            str(Path.cwd() / "tools" / "plantuml" / "plantuml.exe"),
            str(Path.cwd() / "tools" / "plantuml.exe"),
            shutil.which("plantuml"),
        ]
        return PlantUMLRendererBackend._first_existing_path(candidates)

    @staticmethod
    def _find_dot_executable() -> str | None:
        graphviz_root = Path.cwd() / "tools" / "graphviz"
        candidates = [str(path) for path in graphviz_root.rglob("dot.exe")]
        candidates.append(shutil.which("dot"))
        return PlantUMLRendererBackend._first_existing_path(candidates)

    @staticmethod
    def _find_java_executable() -> str | None:
        candidates = [
            shutil.which("java"),
            str(Path.cwd() / "tools" / "jre" / "bin" / "java.exe"),
        ]
        return PlantUMLRendererBackend._first_existing_path(candidates)

    @staticmethod
    def _first_existing_path(candidates: list[str | None]) -> str | None:
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.exists():
                return str(path)
        return None
