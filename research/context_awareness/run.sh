#!/bin/sh
set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)

if [ -x "$ROOT/.venv/bin/python" ]; then
  BASE_PYTHON=${PYTHON:-"$ROOT/.venv/bin/python"}
else
  BASE_PYTHON=${PYTHON:-python3}
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/ada-context-characterization.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

run_backend() {
  backend=$1
  requirements=$2
  output=$3
  mode=${4:-default}
  venv="$TMP/$backend-venv"

  echo "==> $backend: create isolated environment"
  "$BASE_PYTHON" -m venv "$venv" || return 1

  echo "==> $backend: install research dependency"
  if ! "$venv/bin/python" -m pip install --disable-pip-version-check -q -r "$requirements"; then
    echo "WARN: $backend installation failed; continuing with the other resolver." >&2
    return 1
  fi

  if [ "$mode" = "quickadd-safe" ]; then
    echo "==> $backend: disable import-time pickle scorer for research"
    if ! "$venv/bin/python" "$HERE/prepare_quickadd_safe.py"; then
      echo "WARN: $backend safe preparation failed." >&2
      return 1
    fi
  fi

  echo "==> $backend: characterize"
  if ! "$venv/bin/python" "$HERE/run_characterization.py" --backend "$backend" --output "$output"; then
    echo "WARN: $backend characterization failed; continuing with the other resolver." >&2
    return 1
  fi
}

DATEPARSER_RESULT="$TMP/dateparser.json"
QUICKADD_RESULT="$TMP/quickadd.json"
QUICKADD_SAFE_RESULT="$TMP/quickadd-safe.json"
QUICKADD_JSON_RESULT="$TMP/quickadd-json.json"
QUICKADD_MODEL_JSON="$TMP/quickadd-model.json"
DATEPARSER_OK=0
QUICKADD_OK=0
QUICKADD_SAFE_OK=0
QUICKADD_JSON_OK=0

if run_backend dateparser "$HERE/requirements-dateparser.txt" "$DATEPARSER_RESULT"; then
  DATEPARSER_OK=1
fi
if run_backend quickadd "$HERE/requirements-quickadd.txt" "$QUICKADD_RESULT"; then
  QUICKADD_OK=1
  echo "==> quickadd: export scorer model to primitive JSON for research"
  if ! "$TMP/quickadd-venv/bin/python" "$HERE/export_quickadd_model_json.py" --output "$QUICKADD_MODEL_JSON"; then
    echo "WARN: quickadd model JSON export failed." >&2
  fi
fi
if run_backend quickadd-safe "$HERE/requirements-quickadd.txt" "$QUICKADD_SAFE_RESULT" quickadd-safe; then
  QUICKADD_SAFE_OK=1
fi
if [ -f "$QUICKADD_MODEL_JSON" ]; then
  echo "==> quickadd-json: create isolated environment"
  "$BASE_PYTHON" -m venv "$TMP/quickadd-json-venv"
  echo "==> quickadd-json: install research dependency"
  if "$TMP/quickadd-json-venv/bin/python" -m pip install --disable-pip-version-check -q -r "$HERE/requirements-quickadd.txt"; then
    echo "==> quickadd-json: install safe JSON scorer model"
    if "$TMP/quickadd-json-venv/bin/python" "$HERE/prepare_quickadd_json.py" --model-json "$QUICKADD_MODEL_JSON"; then
      echo "==> quickadd-json: characterize"
      if "$TMP/quickadd-json-venv/bin/python" "$HERE/run_characterization.py" --backend quickadd-json --output "$QUICKADD_JSON_RESULT"; then
        QUICKADD_JSON_OK=1
      fi
    fi
  fi
fi

if [ "$DATEPARSER_OK" -eq 1 ]; then
  echo
  echo "--- dateparser ---"
  cat "$DATEPARSER_RESULT"
fi

if [ "$QUICKADD_OK" -eq 1 ]; then
  echo
  echo "--- quickadd ---"
  cat "$QUICKADD_RESULT"
fi

if [ "$QUICKADD_SAFE_OK" -eq 1 ]; then
  echo
  echo "--- quickadd-safe (DummyScorer; no model pickle load) ---"
  cat "$QUICKADD_SAFE_RESULT"
fi

if [ "$QUICKADD_JSON_OK" -eq 1 ]; then
  echo
  echo "--- quickadd-json (trained scorer; JSON runtime load) ---"
  cat "$QUICKADD_JSON_RESULT"
fi

if [ "$DATEPARSER_OK" -eq 1 ] && [ "$QUICKADD_OK" -eq 1 ]; then
  echo
  echo "--- semantic comparison: dateparser vs quickadd ---"
  "$BASE_PYTHON" "$HERE/compare_results.py" "$DATEPARSER_RESULT" "$QUICKADD_RESULT"
fi

if [ "$QUICKADD_OK" -eq 1 ] && [ "$QUICKADD_SAFE_OK" -eq 1 ]; then
  echo
  echo "--- semantic comparison: quickadd vs quickadd-safe ---"
  "$BASE_PYTHON" "$HERE/compare_results.py" "$QUICKADD_RESULT" "$QUICKADD_SAFE_RESULT"
fi

if [ "$QUICKADD_OK" -eq 1 ] && [ "$QUICKADD_JSON_OK" -eq 1 ]; then
  echo
  echo "--- semantic comparison: quickadd vs quickadd-json ---"
  "$BASE_PYTHON" "$HERE/compare_results.py" "$QUICKADD_RESULT" "$QUICKADD_JSON_RESULT"
fi

if [ "$DATEPARSER_OK" -eq 0 ] && [ "$QUICKADD_OK" -eq 0 ] && [ "$QUICKADD_SAFE_OK" -eq 0 ] && [ "$QUICKADD_JSON_OK" -eq 0 ]; then
  echo
  echo "No resolver could be characterized." >&2
  exit 1
fi
