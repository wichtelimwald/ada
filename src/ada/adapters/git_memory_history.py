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
    _OWNERSHIP_MARKER = "ada-memory-history-v1"
    _OWNERSHIP_CONTENT = "Ada file-native Memory history v1\n"

    def __init__(self, root: Path) -> None:
        self.root = root
        git = shutil.which("git")
        if git is None:
            raise GitMemoryHistoryError(
                "Git CLI is required for file-native Memory history"
            )
        self._git = git

    def validate_existing_repository(self) -> None:
        """Reject foreign/pre-existing Git metadata without mutating the root."""

        git_dir = self.root / ".git"
        if git_dir.is_symlink():
            raise GitMemoryHistoryError(
                f"Memory Git directory must not be a symlink: {git_dir}"
            )
        if not git_dir.exists():
            return
        if not git_dir.is_dir():
            raise GitMemoryHistoryError(
                f"Memory Git path is not a directory: {git_dir}"
            )
        self._require_ownership_marker(git_dir)

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
            self._create_ownership_marker(git_dir)
        else:
            self._require_ownership_marker(git_dir)

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

    def _create_ownership_marker(self, git_dir: Path) -> None:
        marker = git_dir / self._OWNERSHIP_MARKER
        try:
            with marker.open("x", encoding="utf-8") as handle:
                handle.write(self._OWNERSHIP_CONTENT)
                handle.flush()
                os.fsync(handle.fileno())
            directory_fd = os.open(
                git_dir,
                os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except (FileExistsError, OSError) as exc:
            raise GitMemoryHistoryError(
                "cannot establish Ada ownership of the Memory Git repository"
            ) from exc

    def _require_ownership_marker(self, git_dir: Path) -> None:
        marker = git_dir / self._OWNERSHIP_MARKER
        if marker.is_symlink():
            raise GitMemoryHistoryError(
                f"Memory Git ownership marker must not be a symlink: {marker}"
            )
        try:
            content = marker.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise GitMemoryHistoryError(
                "refusing to use a pre-existing Git repository that was not "
                "initialized by Ada Memory"
            ) from exc
        except (OSError, UnicodeError) as exc:
            raise GitMemoryHistoryError(
                "cannot verify Ada ownership of the Memory Git repository"
            ) from exc
        if content != self._OWNERSHIP_CONTENT:
            raise GitMemoryHistoryError(
                "Memory Git ownership marker is invalid; refusing repository"
            )

    def capture_external_changes(
        self,
        *,
        message: str = "Capture external Memory edit",
    ) -> bool:
        """Capture current Markdown edits without staging editor/temp artifacts."""

        # `git add` only notices a foreign index lock when there is something to
        # add, so check explicitly before any Ada write is published.
        if os.path.lexists(self.root / ".git" / "index.lock"):
            raise GitMemoryHistoryError(
                "Memory Git index.lock exists; another Git process may be "
                "running and Ada will not remove the lock"
            )
        paths = self._memory_markdown_paths()
        if not paths:
            return False
        self._run("add", "-A", "--", *paths)
        if not self._has_staged_changes(paths):
            return False
        self._run(
            "commit",
            "--only",
            "--no-gpg-sign",
            "-m",
            message,
            "--",
            *paths,
        )
        return True

    def _memory_markdown_paths(self) -> tuple[str, ...]:
        paths: set[str] = set()

        for root_name in sorted(self._OWNED_ROOTS):
            directory = self.root / root_name
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        # Dotfiles are OS/editor artifacts such as AppleDouble
                        # `._x.md` or Emacs `.#x.md`, never Memory entries.
                        if (
                            entry.name.endswith(".md")
                            and not entry.name.startswith(".")
                            and not entry.is_dir(follow_symlinks=False)
                        ):
                            paths.add(f"{root_name}/{entry.name}")
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise GitMemoryHistoryError(
                    f"cannot scan Memory history area: {directory}"
                ) from exc

        tracked = self._run(
            "ls-files",
            "-z",
            "--",
            *sorted(self._OWNED_ROOTS),
        )
        for path in tracked.stdout.split("\0"):
            if path and path.endswith(".md"):
                paths.add(self._validate_owned_path(path))

        return tuple(sorted(paths))

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
            # No HOME/XDG_CONFIG_HOME: user-level Git ignore/attributes files
            # must not change Memory history capture.
            "PATH": os.environ.get("PATH", ""),
            "LC_ALL": "C",
            "LANG": "C",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            # Never discover an enclosing repository if the Memory .git vanishes.
            "GIT_DIR": str(self.root / ".git"),
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
