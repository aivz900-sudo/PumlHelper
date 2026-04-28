import subprocess
import tempfile
import unittest
from pathlib import Path

from app.infrastructure.git.repository_loader import GitRepositoryError, GitRepositoryLoader


class GitRepositoryLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.cache_root = self.root / "cache"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_https_url_gets_stable_cache_path(self) -> None:
        loader = GitRepositoryLoader(cache_root=self.cache_root)
        url = "https://example.com/project/repo.git"

        first_path = loader.cache_path_for_url(url)
        second_path = loader.cache_path_for_url(url)

        self.assertEqual(first_path, second_path)
        self.assertEqual(first_path.parent, self.cache_root)
        self.assertNotEqual(first_path.name, "")

    def test_rejects_non_https_urls(self) -> None:
        loader = GitRepositoryLoader(cache_root=self.cache_root)

        for url in [
            "git@github.com:owner/repo.git",
            "ssh://github.com/owner/repo.git",
            "file:///tmp/repo",
            "C:/repo",
            "http://example.com/repo.git",
        ]:
            with self.subTest(url=url):
                with self.assertRaisesRegex(GitRepositoryError, "HTTPS"):
                    loader.load_repository(url)

    def test_fresh_clone_removes_existing_cache_and_finds_nested_puml(self) -> None:
        runner = FakeGitRunner(
            files_to_create={
                "docs/class.puml": "@startuml\nclass UserService\n@enduml",
                "docs/readme.txt": "not a diagram",
            }
        )
        loader = GitRepositoryLoader(cache_root=self.cache_root, command_runner=runner)
        url = "https://example.com/project/repo.git"
        cache_path = loader.cache_path_for_url(url)
        cache_path.mkdir(parents=True)
        stale_file = cache_path / "stale.puml"
        stale_file.write_text("@startuml\nclass Stale\n@enduml", encoding="utf-8")

        snapshot = loader.load_repository(url)

        self.assertFalse(stale_file.exists())
        self.assertEqual(snapshot.repository_path, str(cache_path))
        self.assertEqual([Path(path).name for path in snapshot.puml_paths], ["class.puml"])
        self.assertEqual(runner.calls[0][0:3], ["git", "clone", "--"])

    def test_refuses_to_delete_path_outside_cache_root(self) -> None:
        loader = GitRepositoryLoader(cache_root=self.cache_root)
        outside_path = self.root / "outside"
        outside_path.mkdir()

        with self.assertRaisesRegex(GitRepositoryError, "cache"):
            loader.delete_cache_directory(outside_path)

    def test_raises_clear_error_when_repository_has_no_puml_files(self) -> None:
        loader = GitRepositoryLoader(
            cache_root=self.cache_root,
            command_runner=FakeGitRunner(files_to_create={"README.md": "empty"}),
        )

        with self.assertRaisesRegex(GitRepositoryError, ".puml"):
            loader.load_repository("https://example.com/project/repo.git")


class FakeGitRunner:
    def __init__(self, files_to_create: dict[str, str]) -> None:
        self.files_to_create = files_to_create
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        target = Path(args[-1])
        target.mkdir(parents=True, exist_ok=True)
        for relative_path, content in self.files_to_create.items():
            path = target / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")


if __name__ == "__main__":
    unittest.main()
