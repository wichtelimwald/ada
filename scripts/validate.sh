#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "error: Python 3 is required but neither 'python3' nor 'python' is available on PATH" >&2
  exit 127
fi

# Force this worktree's src/ ahead of any other installed/editable Ada
# package on sys.path, then prove `ada` actually resolves here. Without
# this, a stale editable install of a different Ada checkout can shadow
# the current worktree and produce false passes/failures (PR #46 review).
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

"$PYTHON" "$SCRIPT_DIR/check_ada_source_precedence.py" "$REPO_ROOT"

"$PYTHON" -m compileall -q src tests

if [ "${ADA_TEST_VERBOSE:-0}" = "1" ]; then
  "$PYTHON" -m unittest discover -s tests -v
else
  "$PYTHON" -m unittest discover -s tests
fi

"$PYTHON" -m ada doctor
