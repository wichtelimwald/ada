from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_ada_source_precedence.py"


def _env_without_pythonpath() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


class ValidateScriptSourcePrecedenceTests(unittest.TestCase):
    """Regression test for PR #46 review finding M3.

    scripts/validate.sh must always exercise this worktree's src/, even when
    another editable Ada installation is reachable on sys.path.
    """

    def test_rejects_a_shadowing_ada_installation(self) -> None:
        with tempfile.TemporaryDirectory() as decoy_root:
            (pathlib.Path(decoy_root) / "ada").mkdir()
            (pathlib.Path(decoy_root) / "ada" / "__init__.py").write_text(
                "marker = 'decoy'\n"
            )

            result = subprocess.run(
                [sys.executable, str(CHECK_SCRIPT), str(REPO_ROOT)],
                cwd=decoy_root,
                env={**_env_without_pythonpath(), "PYTHONPATH": decoy_root},
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("shadowing", result.stderr)

    def test_accepts_worktree_src_prepended_ahead_of_a_shadowing_installation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as decoy_root:
            (pathlib.Path(decoy_root) / "ada").mkdir()
            (pathlib.Path(decoy_root) / "ada" / "__init__.py").write_text(
                "marker = 'decoy'\n"
            )

            worktree_src = str(REPO_ROOT / "src")
            result = subprocess.run(
                [sys.executable, str(CHECK_SCRIPT), str(REPO_ROOT)],
                cwd=decoy_root,
                env={
                    **_env_without_pythonpath(),
                    "PYTHONPATH": worktree_src + os.pathsep + decoy_root,
                },
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validate_script_exports_worktree_src_ahead_of_pythonpath(self) -> None:
        validate_sh = REPO_ROOT / "scripts" / "validate.sh"
        contents = validate_sh.read_text()

        self.assertIn('PYTHONPATH="$REPO_ROOT/src', contents)
        self.assertIn("check_ada_source_precedence.py", contents)


if __name__ == "__main__":
    unittest.main()
