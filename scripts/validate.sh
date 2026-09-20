#!/bin/sh
set -eu

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "error: Python 3 is required but neither 'python3' nor 'python' is available on PATH" >&2
  exit 127
fi

"$PYTHON" -m compileall -q src tests
"$PYTHON" -m unittest discover -s tests -v
"$PYTHON" -m ada doctor
