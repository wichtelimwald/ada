from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import Iterable


class GitMemoryHistoryError(RuntimeError):
    """Git-backed Memory history could not be updated safely."""


class GitMemoryHistory:
    """Small Git CLI adapter for one file-native Memory root.

    Current files remain authoritative. This adapter records history only; callers
    must never use it to rehydrate current Memory.
    """

    _OWNED_ROOTS = frozenset({"memory", "learning"})

    def __init__(self, root: Path) -> None:
        self.root = root
        git = shutil.which("git")
        if git is None:
            raise GitMemoryHistoryError(
                "Git CLI is required for file-native Memory history"
            )
        self._git = git

    def ensure_initialized(self) -> None:
        git_dir = self.root / ".git"
        if git_dir.is_symlink():
            raise GitMemoryHistoryError(
                f"Memory Git directory must not be a symlink: {git_dir}"
            )
        if git_dir.exists() and not git_dir.is_dir():
            raise GitMemoryHistoryError(
                f"Memory Git path is not a directory: {git_dir}"
            )

        if not git_dir.exists():
            with TemporaryDirectory(prefix="ada-git-template-") as template:
                self._run(
                    "init",
                    "--quiet",
                    extra_env={"GIT_TEMPLATE_DIR": template},
                )

        head = self._run(
            "rev-parse",
            "--verify",
            "HEAD",
            check=False,
        )
        if head.returncode != 0:
            self._run(
                "commit",
                "--allow-empty",
                "--no-gpg-sign",
                "-m",
                "Initialize Ada Memory history",
            )

    def capture_external_changes(self) -> bool:
        """Capture all current Memory-area edits already present in the worktree."""

        paths = ("memory", "learning")
        self._run("add", "-A", "--", *paths)
        if not self._has_staged_changes(paths):
            return False
        self._run(
            "commit",
            "--only",
            "--no-gpg-sign",
            "-m",
            "Capture external Memory edit",
            "--",
            *paths,
        )
        return True

    def capture_ada_write(
        self,
        paths: Iterable[str],
        *,
        reason: str,
    ) -> bool:
        """Capture only paths intentionally changed by one Ada operation."""

        normalized = tuple(self._validate_owned_path(path) for path in paths)
        if not normalized:
            raise ValueError("at least one Memory history path is required")

        self._run("add", "-A", "--", *normalized)
        if not self._has_staged_changes(normalized):
            return False
        self._run(
            "commit",
            "--only",
            "--no-gpg-sign",
            "-m",
            f"Ada Memory: {reason}",
            "--",
            *normalized,
        )
        return True

    def has_path_history(self, path: str) -> bool:
        normalized = self._validate_owned_path(path)
        result = self._run(
            "log",
            "--format=%H",
            "--all",
            "--",
            normalized,
        )
        return bool(result.stdout.strip())

    def head(self) -> str:
        result = self._run("rev-parse", "HEAD")
        return result.stdout.strip()

    def _has_staged_changes(self, paths: tuple[str, ...]) -> bool:
        result = self._run(
            "diff",
            "--cached",
            "--quiet",
            "--",
            *paths,
            check=False,
        )
        if result.returncode == 0:
            return False
        if result.returncode == 1:
            return True
        raise GitMemoryHistoryError(
            self._format_failure(("diff", "--cached", "--quiet", "--", *paths), result)
        )

    @classmethod
    def _validate_owned_path(cls, path: str) -> str:
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"invalid Memory history path: {path!r}")
        if not candidate.parts or candidate.parts[0] not in cls._OWNED_ROOTS:
            raise ValueError(f"path is outside Memory-owned areas: {path!r}")
        return candidate.as_posix()

    def _run(
        self,
        *args: str,
        check: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "LC_ALL": "C",
            "LANG": "C",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_AUTHOR_NAME": "Ada Memory History",
            "GIT_AUTHOR_EMAIL": "ada-memory@localhost.invalid",
            "GIT_COMMITTER_NAME": "Ada Memory History",
            "GIT_COMMITTER_EMAIL": "ada-memory@localhost.invalid",
        }
        if extra_env:
            env.update(extra_env)

        command = [
            self._git,
            "-C",
            str(self.root),
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgSign=false",
            *args,
        ]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
        except OSError as exc:
            raise GitMemoryHistoryError(
                f"cannot execute Git for Memory history: {exc}"
            ) from exc

        if check and result.returncode != 0:
            raise GitMemoryHistoryError(self._format_failure(args, result))
        return result

    @staticmethod
    def _format_failure(
        args: tuple[str, ...],
        result: subprocess.CompletedProcess[str],
    ) -> str:
        detail = (result.stderr or result.stdout).strip()
        if len(detail) > 500:
            detail = detail[:500] + "..."
        command = " ".join(args[:3])
        if detail:
            return f"Memory history Git command failed ({command}): {detail}"
        return f"Memory history Git command failed ({command})"
