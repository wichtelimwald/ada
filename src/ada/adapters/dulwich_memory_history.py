from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import stat
import time

from dulwich.object_store import tree_lookup_path
from dulwich.objects import Blob, Commit, Tree
from dulwich.repo import Repo


_HISTORY_BRANCH = b"refs/heads/memory"
_HISTORY_IDENTITY = b"Ada Memory <memory@local.invalid>"


class MemoryHistoryError(RuntimeError):
    """Git-style Memory history could not be read or updated safely."""


class DulwichMemoryHistory:
    """Per-root Git history adapter that never checks content out to Memory.

    Current Markdown is supplied by the caller as an explicit snapshot. The
    adapter stores recovery/versioning revisions only and never mutates the
    authoritative working files.
    """

    def __init__(self, history_root: str | Path) -> None:
        self.root = Path(history_root)
        try:
            if self.root.is_symlink():
                raise MemoryHistoryError(
                    f"Memory history root must not be a symlink: {self.root}"
                )
            if not self.root.exists():
                self.root.mkdir(mode=0o700, parents=False)
                repo = Repo.init_bare(str(self.root))
                repo.refs.set_symbolic_ref(b"HEAD", _HISTORY_BRANCH)
                repo.close()
            self._open_repo().close()
        except MemoryHistoryError:
            raise
        except Exception as exc:
            raise MemoryHistoryError(
                f"cannot initialize Memory history at {self.root}"
            ) from exc

    def capture_snapshot(
        self,
        snapshot: Mapping[str, bytes],
        *,
        reason: str,
    ) -> bool:
        reason = reason.strip()
        if not reason:
            raise ValueError("Memory history reason must not be empty")

        try:
            with self._open_repo() as repo:
                tree_id = self._store_snapshot_tree(repo, snapshot)
                parent = self._head_or_none(repo)
                if parent is not None:
                    previous = repo[parent]
                    if not isinstance(previous, Commit):
                        raise MemoryHistoryError("Memory history HEAD is not a commit")
                    if previous.tree == tree_id:
                        return False

                now = int(time.time())
                commit = Commit()
                commit.tree = tree_id
                commit.parents = [] if parent is None else [parent]
                commit.author = _HISTORY_IDENTITY
                commit.committer = _HISTORY_IDENTITY
                commit.author_time = now
                commit.commit_time = now
                commit.author_timezone = 0
                commit.commit_timezone = 0
                commit.message = reason.encode("utf-8")
                repo.object_store.add_object(commit)
                repo.refs[_HISTORY_BRANCH] = commit.id
                repo.refs.set_symbolic_ref(b"HEAD", _HISTORY_BRANCH)
                return True
        except MemoryHistoryError:
            raise
        except Exception as exc:
            raise MemoryHistoryError("cannot capture Memory history revision") from exc

    def has_seen_entry_id(self, entry_id: str) -> bool:
        candidates = (
            f"memory/{entry_id}.md".encode("utf-8"),
            f"learning/{entry_id}.md".encode("utf-8"),
        )
        try:
            with self._open_repo() as repo:
                if self._head_or_none(repo) is None:
                    return False
                for item in repo.get_walker(include=[repo.head()]):
                    commit = item.commit
                    for path in candidates:
                        try:
                            tree_lookup_path(repo.__getitem__, commit.tree, path)
                        except KeyError:
                            continue
                        else:
                            return True
                return False
        except MemoryHistoryError:
            raise
        except Exception as exc:
            raise MemoryHistoryError("cannot inspect Memory history identities") from exc

    def _open_repo(self) -> Repo:
        try:
            return Repo(str(self.root))
        except Exception as exc:
            raise MemoryHistoryError(
                f"invalid or unreadable Memory history at {self.root}"
            ) from exc

    @staticmethod
    def _head_or_none(repo: Repo) -> bytes | None:
        try:
            return repo.head()
        except KeyError:
            return None

    @staticmethod
    def _store_snapshot_tree(
        repo: Repo,
        snapshot: Mapping[str, bytes],
    ) -> bytes:
        by_area: dict[str, list[tuple[str, bytes]]] = {
            "memory": [],
            "learning": [],
        }
        for relative, content in snapshot.items():
            parts = Path(relative).parts
            if len(parts) != 2 or parts[0] not in by_area:
                raise MemoryHistoryError(
                    f"history snapshot path is outside Memory areas: {relative}"
                )
            name = parts[1]
            if not name.endswith(".md") or name in {".", ".."}:
                raise MemoryHistoryError(
                    f"history snapshot path is not a Memory Markdown file: {relative}"
                )
            by_area[parts[0]].append((name, bytes(content)))

        root_tree = Tree()
        for area in ("memory", "learning"):
            entries = by_area[area]
            if not entries:
                continue
            area_tree = Tree()
            for name, content in sorted(entries):
                blob = Blob.from_string(content)
                repo.object_store.add_object(blob)
                area_tree.add(
                    name.encode("utf-8"),
                    stat.S_IFREG | 0o600,
                    blob.id,
                )
            repo.object_store.add_object(area_tree)
            root_tree.add(
                area.encode("ascii"),
                stat.S_IFDIR,
                area_tree.id,
            )

        repo.object_store.add_object(root_tree)
        return root_tree.id
