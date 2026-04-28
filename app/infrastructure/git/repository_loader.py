from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class GitRepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class GitRepositorySnapshot:
    repository_path: str
    puml_paths: list[str]


class GitRepositoryLoader:
    def __init__(
        self,
        cache_root: str | Path = ".vkr_puml_git_cache",
        git_executable: str = "git",
        command_runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.cache_root = Path(cache_root)
        self._git_executable = git_executable
        self._command_runner = command_runner or self._run_command

    def load_repository(self, repository_url: str) -> GitRepositorySnapshot:
        normalized_url = repository_url.strip()
        repository_path = self.cache_path_for_url(normalized_url)
        self.delete_cache_directory(repository_path)
        repository_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = self._command_runner(
                [self._git_executable, "clone", "--", normalized_url, str(repository_path)]
            )
        except FileNotFoundError as error:
            raise GitRepositoryError("Git executable was not found.") from error

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "unknown git error").strip()
            raise GitRepositoryError(f"Git clone failed: {details}")

        puml_paths = self._find_puml_files(repository_path)
        if not puml_paths:
            raise GitRepositoryError("Repository does not contain .puml files.")

        return GitRepositorySnapshot(
            repository_path=str(repository_path),
            puml_paths=[str(path) for path in puml_paths],
        )

    def cache_path_for_url(self, repository_url: str) -> Path:
        self._validate_https_url(repository_url)
        digest = hashlib.sha256(repository_url.strip().encode("utf-8")).hexdigest()[:16]
        return self.cache_root / digest

    def delete_cache_directory(self, path: str | Path) -> None:
        cache_root = self.cache_root.resolve(strict=False)
        target = Path(path).resolve(strict=False)
        if target == cache_root or not target.is_relative_to(cache_root):
            raise GitRepositoryError("Refusing to delete a path outside the Git cache.")
        if not target.exists():
            return
        shutil.rmtree(target, onexc=self._make_writable_and_retry)

    def _find_puml_files(self, repository_path: Path) -> list[Path]:
        return sorted(path for path in repository_path.rglob("*.puml") if path.is_file())

    def _validate_https_url(self, repository_url: str) -> None:
        parsed = urlparse(repository_url.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise GitRepositoryError("Only public HTTPS Git repository URLs are supported.")

    def _run_command(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    @staticmethod
    def _make_writable_and_retry(
        function: Callable[[str], object],
        path: str,
        _error: BaseException,
    ) -> None:
        os.chmod(path, stat.S_IWRITE)
        function(path)
