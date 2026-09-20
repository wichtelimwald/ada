#!/bin/sh
set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
VERBOSE=${VERBOSE:-0}

if [ -x "$ROOT/.venv/bin/python" ]; then
  BASE_PYTHON=${PYTHON:-"$ROOT/.venv/bin/python"}
else
  BASE_PYTHON=${PYTHON:-python3}
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/ada-context-characterization.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

detail() {
  if [ "$VERBOSE" = "1" ]; then
    echo "$@"
  fi
}

run_quiet() {
  label=$1
  shift
  log="$TMP/$label.log"
  if "$@" >"$log" 2>&1; then
    if [ "$VERBOSE" = "1" ]; then
      cat "$log"
    fi
    return 0
  fi
  cat "$log" >&2
  return 1
}

run_backend() {
  backend=$1
  requirements=$2
  output=$3
  mode=${4:-default}
  require_all=${5:-0}
  venv="$TMP/$backend-venv"
  warnings="$TMP/$backend-warnings.log"

  detail "==> $backend: create isolated environment"
  "$BASE_PYTHON" -m venv "$venv" || return 1

  detail "==> $backend: install research dependency"
  if ! "$venv/bin/python" -m pip install --disable-pip-version-check -q -r "$requirements"; then
    echo "WARN: $backend installation failed; continuing with the other resolver." >&2
    return 1
  fi

  if [ "$backend" != "dateparser" ]; then
    detail "==> $backend: surface parser timeouts for research"
    if ! run_quiet "$backend-timeout" "$venv/bin/python" "$HERE/prepare_quickadd_timeout.py"; then
      echo "WARN: $backend timeout instrumentation failed." >&2
      return 1
    fi
  fi

  if [ "$mode" = "quickadd-safe" ]; then
    detail "==> $backend: disable import-time pickle scorer for research"
    if ! run_quiet "$backend-prepare" "$venv/bin/python" "$HERE/prepare_quickadd_safe.py"; then
      echo "WARN: $backend safe preparation failed." >&2
      return 1
    fi
  fi

  detail "==> $backend: characterize"
  if [ "$require_all" = "1" ]; then
    "$venv/bin/python" "$HERE/run_characterization.py" \
      --backend "$backend" --output "$output" --summary --require-all-expected \
      2>"$warnings"
  else
    "$venv/bin/python" "$HERE/run_characterization.py" \
      --backend "$backend" --output "$output" --summary \
      2>"$warnings"
  fi
  status=$?
  if [ "$status" -ne 0 ]; then
    cat "$warnings" >&2
    echo "WARN: $backend characterization failed; continuing with the other resolver." >&2
    return "$status"
  fi
}

report_warnings() {
  invalid_escape=0
  other_warning=0

  for backend in dateparser quickadd quickadd-safe quickadd-json; do
    log="$TMP/$backend-warnings.log"
    if [ ! -s "$log" ]; then
      continue
    fi

    if grep -q 'SyntaxWarning:.*invalid escape sequence' "$log"; then
      invalid_escape=1
    else
      other_warning=1
      echo "WARN: $backend emitted warnings; use VERBOSE=1 for details." >&2
    fi

    if [ "$VERBOSE" = "1" ]; then
      echo
      echo "--- $backend warnings ---" >&2
      cat "$log" >&2
    fi
  done

  if [ "$invalid_escape" -eq 1 ]; then
    echo "WARN: ctparse 0.6.5 emits Python 3.14 invalid-escape SyntaxWarning(s) in patched research environments (upstream code)." >&2
  fi

  return "$other_warning"
}

print_raw_results() {
  if [ "$VERBOSE" != "1" ]; then
    return
  fi

  for name in dateparser quickadd quickadd-safe quickadd-json; do
    file="$TMP/$name.json"
    if [ -f "$file" ]; then
      echo
      echo "--- $name raw result ---"
      cat "$file"
    fi
  done

  for name in dateparser-vs-quickadd quickadd-vs-quickadd-safe quickadd-vs-quickadd-json; do
    file="$TMP/$name.json"
    if [ -f "$file" ]; then
      echo
      echo "--- $name comparison ---"
      cat "$file"
    fi
  done
}

DATEPARSER_RESULT="$TMP/dateparser.json"
QUICKADD_RESULT="$TMP/quickadd.json"
QUICKADD_SAFE_RESULT="$TMP/quickadd-safe.json"
QUICKADD_JSON_RESULT="$TMP/quickadd-json.json"
QUICKADD_MODEL_JSON="$TMP/quickadd-model.json"
DATEPARSER_QUICKADD_COMPARE="$TMP/dateparser-vs-quickadd.json"
QUICKADD_SAFE_COMPARE="$TMP/quickadd-vs-quickadd-safe.json"
QUICKADD_JSON_COMPARE="$TMP/quickadd-vs-quickadd-json.json"

DATEPARSER_OK=0
QUICKADD_OK=0
QUICKADD_SAFE_OK=0
QUICKADD_JSON_OK=0
INVARIANT_OK=1

echo "Ada context-awareness characterization"
echo

if run_backend dateparser "$HERE/requirements-dateparser.txt" "$DATEPARSER_RESULT"; then
  DATEPARSER_OK=1
fi

if run_backend quickadd "$HERE/requirements-quickadd.txt" "$QUICKADD_RESULT" default 1; then
  QUICKADD_OK=1
  detail "==> quickadd: export scorer model to primitive JSON for research"
  if ! run_quiet quickadd-export "$TMP/quickadd-venv/bin/python" \
    "$HERE/export_quickadd_model_json.py" --output "$QUICKADD_MODEL_JSON"; then
    echo "WARN: quickadd model JSON export failed." >&2
    INVARIANT_OK=0
  fi
else
  INVARIANT_OK=0
fi

if run_backend quickadd-safe "$HERE/requirements-quickadd.txt" "$QUICKADD_SAFE_RESULT" quickadd-safe; then
  QUICKADD_SAFE_OK=1
fi

if [ -f "$QUICKADD_MODEL_JSON" ]; then
  detail "==> quickadd-json: create isolated environment"
  if ! "$BASE_PYTHON" -m venv "$TMP/quickadd-json-venv"; then
    echo "WARN: quickadd-json environment creation failed." >&2
    INVARIANT_OK=0
  else
    detail "==> quickadd-json: install research dependency"
    if "$TMP/quickadd-json-venv/bin/python" -m pip install --disable-pip-version-check -q -r "$HERE/requirements-quickadd.txt"; then
      detail "==> quickadd-json: surface parser timeouts for research"
      if ! run_quiet quickadd-json-timeout "$TMP/quickadd-json-venv/bin/python" \
        "$HERE/prepare_quickadd_timeout.py"; then
        echo "WARN: quickadd-json timeout instrumentation failed." >&2
        INVARIANT_OK=0
      else
        detail "==> quickadd-json: install safe JSON scorer model"
        if run_quiet quickadd-json-prepare "$TMP/quickadd-json-venv/bin/python" \
          "$HERE/prepare_quickadd_json.py" --model-json "$QUICKADD_MODEL_JSON"; then
        detail "==> quickadd-json: characterize"
        "$TMP/quickadd-json-venv/bin/python" "$HERE/run_characterization.py" \
          --backend quickadd-json --output "$QUICKADD_JSON_RESULT" \
          --summary --require-all-expected \
          2>"$TMP/quickadd-json-warnings.log"
        status=$?
        if [ "$status" -eq 0 ]; then
          QUICKADD_JSON_OK=1
        else
          cat "$TMP/quickadd-json-warnings.log" >&2
          INVARIANT_OK=0
        fi
        else
          echo "WARN: quickadd-json safe preparation failed." >&2
          INVARIANT_OK=0
        fi
      fi
    else
      echo "WARN: quickadd-json installation failed." >&2
      INVARIANT_OK=0
    fi
  fi
else
  INVARIANT_OK=0
fi

echo
echo "Semantic comparisons"

if [ "$DATEPARSER_OK" -eq 1 ] && [ "$QUICKADD_OK" -eq 1 ]; then
  "$BASE_PYTHON" "$HERE/compare_results.py" \
    "$DATEPARSER_RESULT" "$QUICKADD_RESULT" \
    --output "$DATEPARSER_QUICKADD_COMPARE" --summary
fi

if [ "$QUICKADD_OK" -eq 1 ] && [ "$QUICKADD_SAFE_OK" -eq 1 ]; then
  "$BASE_PYTHON" "$HERE/compare_results.py" \
    "$QUICKADD_RESULT" "$QUICKADD_SAFE_RESULT" \
    --output "$QUICKADD_SAFE_COMPARE" --summary
fi

if [ "$QUICKADD_OK" -eq 1 ] && [ "$QUICKADD_JSON_OK" -eq 1 ]; then
  if ! "$BASE_PYTHON" "$HERE/compare_results.py" \
    "$QUICKADD_RESULT" "$QUICKADD_JSON_RESULT" \
    --output "$QUICKADD_JSON_COMPARE" --summary --require-all-agreement; then
    INVARIANT_OK=0
  fi
fi

echo
report_warnings || true

print_raw_results

if [ "$DATEPARSER_OK" -eq 0 ] && [ "$QUICKADD_OK" -eq 0 ] && [ "$QUICKADD_SAFE_OK" -eq 0 ] && [ "$QUICKADD_JSON_OK" -eq 0 ]; then
  echo "No resolver could be characterized." >&2
  exit 1
fi

if [ "$INVARIANT_OK" -ne 1 ]; then
  echo "Research characterization: FAILED regression gate" >&2
  exit 1
fi

echo "Research characterization: OK"
