#!/usr/bin/env python3
"""Dependency-free, research-only Markdown/Git/search control for ADR-0008."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


def git(root: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Synthetic fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout


def init(root: Path) -> None:
    root.mkdir()
    git(root, "init", "-q")


def snapshot(root: Path, reason: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", reason)


def write(root: Path, name: str, content: str) -> None:
    (root / name).write_text(content, encoding="utf-8")


def search(root: Path, term: str) -> list[str]:
    """The entire intentionally simple baseline: read current Markdown only."""
    return sorted(
        path.name
        for path in root.glob("*.md")
        if term.casefold() in path.read_text(encoding="utf-8").casefold()
    )


def probe_failure_modes(base: Path) -> list[str]:
    """Demonstrate unsafe baseline behaviors, without pretending to fix them."""
    root = base / "failure-probes"
    init(root)
    write(root, "ada.md", "Current: 16:00\nSource: SRC_ADA\n")
    write(root, "editor.md", "Current: 17:00\nSource: SRC_EDITOR\n")
    snapshot(root, "initial synthetic notes")

    # Unscoped staging attributes an unrelated manual change to Ada.
    write(root, "editor.md", "Current: 17:30\nSource: SRC_EDITOR_NEW\n")
    write(root, "ada.md", "Current: 16:30\nSource: SRC_ADA_NEW\n")
    snapshot(root, "Ada changed ada.md")
    assert "editor.md" in git(root, "show", "--format=%s", "--name-only", "HEAD")
    # A path-restricted commit must not absorb unrelated content that another
    # tool/editor already staged in the shared index.
    write(root, "editor.md", "Current: 17:45\nSource: SRC_EDITOR_LATER\n")
    git(root, "add", "--", "editor.md")
    write(root, "ada.md", "Current: 16:45\nSource: SRC_ADA_LATER\n")
    git(root, "commit", "-q", "--only", "-m", "Ada updated scoped note", "--", "ada.md")
    assert "editor.md" not in git(root, "show", "--format=", "--name-only", "HEAD")
    assert git(root, "diff", "--cached", "--name-only").strip() == "editor.md"
    git(root, "commit", "-q", "-m", "external edit captured")

    # A stale lock stops history capture after a file write; never silently
    # remove a possibly live lock.
    write(root, "ada.md", "Current: 16:50\nSource: SRC_ADA_LOCKED\n")
    lock = root / ".git" / "index.lock"
    lock.write_text("synthetic stale lock", encoding="utf-8")
    try:
        try:
            git(root, "add", "--", "ada.md")
        except subprocess.CalledProcessError as exc:
            assert "index.lock" in exc.stderr
        else:
            raise AssertionError("Git accepted a locked index")
    finally:
        lock.unlink()  # Fixture cleanup only, not a production recovery rule.
    assert git(root, "diff", "--name-only").strip() == "ada.md"
    git(root, "commit", "-q", "--only", "-m", "capture after lock recovery", "--", "ada.md")

    # Model the actual stale-write sequence: Ada reads, an editor changes the
    # file, then Ada writes content derived from its stale snapshot.
    note = root / "ada.md"
    stale_read = note.read_text(encoding="utf-8")
    expected = hashlib.sha256(stale_read.encode("utf-8")).digest()
    note.write_text(
        "Current: 17:00\nSource: SRC_EXTERNAL\nEditor-note: keep me\n",
        encoding="utf-8",
    )
    assert hashlib.sha256(note.read_bytes()).digest() != expected
    stale_ada_write = stale_read.replace("16:50", "16:55")
    note.write_text(stale_ada_write, encoding="utf-8")
    assert "Editor-note: keep me" not in note.read_text(encoding="utf-8")

    shared, private = base / "scope-shared", base / "scope-private"
    init(shared)
    init(private)
    write(shared, "appointment.md", "SHARED_SECRET_CANARY\n")
    snapshot(shared, "synthetic shared state")
    write(private, "appointment.md", "SHARED_SECRET_CANARY\n")
    snapshot(private, "synthetic private state")
    (shared / "appointment.md").unlink()
    snapshot(shared, "remove current shared copy")
    assert search(shared, "SHARED_SECRET_CANARY") == []
    assert "SHARED_SECRET_CANARY" in git(shared, "log", "--all", "-p")

    # Direct Markdown/search does not automatically retire stale sources,
    # classify conflicts, or exclude superseded sections from retrieval.
    write(root, "stale-source.md", "Current: Thursday 17:00\nSource: SRC_THURSDAY\n")
    snapshot(root, "record sourced claim")
    write(root, "stale-source.md", "Current: Friday 17:00\nSource: SRC_THURSDAY\n")
    assert search(root, "Current: Friday 17:00") == ["stale-source.md"]
    assert "SRC_THURSDAY" in (root / "stale-source.md").read_text(encoding="utf-8")

    write(root, "pickup-16.md", "# Pickup\nClaim: 16:00\nSource: SRC_16\n")
    write(root, "pickup-17.md", "# Pickup\nClaim: 17:00\nSource: SRC_17\n")
    assert search(root, "# Pickup") == ["pickup-16.md", "pickup-17.md"]
    assert all(
        "Unresolved" not in (root / name).read_text(encoding="utf-8")
        for name in ("pickup-16.md", "pickup-17.md")
    )

    write(
        root,
        "superseded.md",
        "# Music\nCurrent: Thursday 17:00\n"
        "Superseded (not current): Wednesday 17:00\n",
    )
    assert search(root, "Wednesday 17:00") == ["superseded.md"]
    return [
        "unscoped staging attributes an external edit to an Ada commit",
        "a Git index lock prevents capture until deliberate recovery",
        "an intervening editor write invalidates Ada's old file snapshot",
        "moving a shared note to private leaves the shared Git history readable",
        "plain Markdown does not automatically retire old sources or label contradictions",
    ]


def run() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ada-memory-control-") as tmp:
        base = Path(tmp)
        private_a, private_b, shared = (base / item for item in ("private-a", "private-b", "shared"))
        for root in (private_a, private_b, shared):
            init(root)

        write(private_a, "preference.md", "# Preference\nEmail summaries preferred.\nSource: SRC_PREF\n")
        write(private_a, "music.md", "# Music lesson\nCurrent: Wednesday 17:00\nSource: SRC_WED\n")
        write(private_a, "pickup-16.md", "# Pickup\nClaim: 16:00\nSource: SRC_16\n")
        write(private_b, "secret.md", "# Private B\nPRIVATE_B_CANARY\n")
        write(shared, "shared.md", "# Shared household\nShared plan\n")
        for root in (private_a, private_b, shared):
            snapshot(root, "initial synthetic state")

        # An explicit correction replaces the current claim; Git retains the old one.
        write(private_a, "music.md", "# Music lesson\nCurrent: Thursday 17:00\nSource: SRC_THU\n")
        snapshot(private_a, "Ada accepted explicit correction")
        assert search(private_a, "Current: Thursday 17:00") == ["music.md"]
        assert search(private_a, "Current: Wednesday 17:00") == []

        # A separate, unresolved claim must not rewrite the first claim.
        write(private_a, "pickup-17.md", "# Pickup\nClaim: 17:00\nSource: SRC_17\n")
        snapshot(private_a, "Ada retained independent conflicting claim")
        assert search(private_a, "Claim: 16:00") == ["pickup-16.md"]
        assert search(private_a, "Claim: 17:00") == ["pickup-17.md"]

        # Simulate a direct editor; no watcher or authenticated editor identity.
        write(private_a, "music.md", "# Music lesson\nCurrent: Friday 17:00\n")
        diff = git(private_a, "diff", "--", "music.md")
        assert "-Source: SRC_THU" in diff and "+Current: Friday 17:00" in diff
        assert search(private_a, "Current: Friday 17:00") == ["music.md"]
        assert search(private_a, "SRC_THU") == []
        snapshot(private_a, "synthetic capture of external edit")

        # Deleting current Markdown does not erase Git objects or backups.
        (private_a / "preference.md").unlink()
        snapshot(private_a, "remove current preference note")
        assert search(private_a, "SRC_PREF") == []
        history = git(private_a, "log", "--all", "-p", "--", "preference.md")
        assert "SRC_PREF" in history

        # Separate roots are query filters, not OS-enforced access control.
        assert search(private_a, "PRIVATE_B_CANARY") == []
        assert "PRIVATE_B_CANARY" in (private_b / "secret.md").read_text(encoding="utf-8")

        return {
            "fixture": "synthetic, standard-library Python plus local git",
            "demonstrated": [
                "direct read/search sees the current Markdown after an outside edit",
                "explicit correction replaces the current claim",
                "unresolved conflicting claims remain separate",
                "a direct edit can be detected by Git diff and captured when a snapshot runs",
                "deletion removes the note from current read/search",
            ],
            "failure_probes": probe_failure_modes(base),
            "open_gates": [
                "automatic external-edit capture, path-restricted commits, and crash/concurrency handling in both directions",
                "editor identity is not authenticated by Git commit metadata",
                "history remains recoverable by design; exclusion from future Ada indexes is untested",
                "scope narrowing needs explicit non-revocation semantics; historical purge is a separate policy",
                "separate roots under the same OS principal do not enforce privacy",
                "search relevance, section-aware current/superseded handling, size and latency on representative vaults are unmeasured",
                "source/document-reference lifecycle and generalized semantic validation are untested",
            ],
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
