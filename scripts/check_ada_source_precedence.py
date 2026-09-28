"""Fail unless `ada` would import from this repository's own `src/`.

Guards scripts/validate.sh against a stale editable Ada installation (for
example a different worktree's `pip install -e`) shadowing the current
worktree on sys.path. See PR #46 review finding M3.
"""

from __future__ import annotations

import pathlib
import sys


def main(repo_root: str) -> int:
    expected = (pathlib.Path(repo_root) / "src" / "ada").resolve()

    import ada

    actual = pathlib.Path(ada.__file__).resolve().parent
    if actual != expected:
        print(
            f"error: 'ada' imported from {actual}, expected {expected}. "
            "Another Ada installation is shadowing this worktree on "
            "sys.path/PYTHONPATH.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
