#!/bin/sh
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HERE="$ROOT/research/memory/reme-langmem"
DRIVER="$HERE/driver.py"
CONFIG="$HERE/config.yaml"
PYTHON_BIN="${PYTHON_BIN:-python3.14}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
STAMP="$(date '+%Y%m%d-%H%M%S')"
BASE="$ROOT/artifacts/research/memory/reme-langmem"
OUT="${ADA_REME_LANGMEM_ROOT:-$BASE/run-$STAMP}"
VENV="$OUT/venv"
AUDIT_VENV="$OUT/audit-venv"
WORKSPACE="$OUT/workspace"
STEPS="$OUT/steps.tsv"

mkdir -p "$OUT/logs" "$WORKSPACE"
if [ -z "${ADA_REME_LANGMEM_ROOT:-}" ]; then
  mkdir -p "$BASE"
  ln -sfn "run-$STAMP" "$BASE/latest"
fi
: > "$STEPS"

now_seconds() {
  date '+%s'
}

record() {
  printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$STEPS"
}

run_step() {
  name="$1"
  shift
  log="$OUT/logs/$name.log"
  start="$(now_seconds)"
  printf '==> %s\n' "$name"
  if "$@" >"$log" 2>&1; then
    end="$(now_seconds)"
    record "$name" PASS "$((end - start))"
    printf '    PASS\n'
    return 0
  fi
  rc=$?
  end="$(now_seconds)"
  record "$name" FAIL "$((end - start))"
  printf '    FAIL (exit %s; see %s)\n' "$rc" "$log"
  tail -n 40 "$log" 2>/dev/null || true
  return "$rc"
}

run_optional() {
  name="$1"
  shift
  log="$OUT/logs/$name.log"
  start="$(now_seconds)"
  printf '==> %s\n' "$name"
  if "$@" >"$log" 2>&1; then
    end="$(now_seconds)"
    record "$name" PASS "$((end - start))"
    printf '    PASS\n'
    return 0
  fi
  rc=$?
  end="$(now_seconds)"
  record "$name" FINDING "$((end - start))"
  printf '    FINDING (exit %s; see %s)\n' "$rc" "$log"
  tail -n 30 "$log" 2>/dev/null || true
  return 0
}

finish() {
  if [ -x "$VENV/bin/python" ]; then
    "$VENV/bin/python" "$DRIVER" summary --result-dir "$OUT" >/dev/null 2>&1 || true
  fi
  if [ -f "$OUT/SUMMARY.md" ]; then
    cat "$OUT/SUMMARY.md"
  fi
  printf '\nReview bundle: %s/REVIEW-BUNDLE.txt\n' "$OUT"
}

critical() {
  name="$1"
  shift
  if ! run_step "$name" "$@"; then
    finish
    exit 1
  fi
}

preflight() {
  [ "$(uname -s)" = "Darwin" ] || {
    echo "This final characterization intentionally targets macOS." >&2
    return 1
  }
  [ "$(uname -m)" = "arm64" ] || {
    echo "Expected Apple Silicon arm64; got $(uname -m)." >&2
    return 1
  }
  command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
    echo "Missing $PYTHON_BIN." >&2
    return 1
  }
  "$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info[:2] != (3, 14):
    raise SystemExit(f"Expected Python 3.14, got {sys.version}")
PY
  command -v ollama >/dev/null 2>&1 || {
    echo "Ollama CLI is required." >&2
    return 1
  }
  ollama show "$OLLAMA_MODEL" >/dev/null 2>&1 || {
    echo "Required local model is missing: $OLLAMA_MODEL" >&2
    return 1
  }

  {
    echo "timestamp=$(date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "branch=$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
    echo "head=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
    echo "uname=$(uname -a)"
    echo "os=$(sw_vers 2>/dev/null | tr '\n' ';' || true)"
    echo "arch=$(uname -m)"
    "$PYTHON_BIN" --version
    ollama --version
    echo "ollama_model=$OLLAMA_MODEL"
  } > "$OUT/environment.txt"
}

create_venv() {
  "$PYTHON_BIN" -m venv "$VENV"
  "$VENV/bin/python" -m pip --version
}

install_runtime() {
  # Install Ada itself plus both candidate components into one environment.
  "$VENV/bin/python" -m pip install "$ROOT" "reme-ai[as]==0.4.1.12" "langmem==0.0.30" "langchain-ollama==1.1.0" "langchain-core>=1.3.3" "langgraph>=1.0.10,<2" "langgraph-checkpoint>=4.1.1"
  "$VENV/bin/python" -m pip check
  "$VENV/bin/python" - <<'PY'
import importlib.metadata as md
import reme
if reme.__version__ != "0.4.1.12":
    raise SystemExit(f"Expected ReMe 0.4.1.12, got {reme.__version__}")
if md.version("ada-assistant") != "0.0.1":
    raise SystemExit("Ada package missing from combined environment")
print("reme", reme.__version__)
print("ada-assistant", md.version("ada-assistant"))
PY
}
capture_runtime() {
  "$VENV/bin/python" -m pip freeze > "$OUT/pip-freeze.txt"
  grep -v '^ada-assistant' "$OUT/pip-freeze.txt" > "$OUT/pip-audit-requirements.txt"
  "$VENV/bin/python" -m pip inspect --local > "$OUT/pip-inspect.json"
  "$VENV/bin/python" "$DRIVER" inventory --out "$OUT/inventory.json"
  {
    echo "venv_kib=$(du -sk "$VENV" | awk '{print $1}')"
    echo "venv_files=$(find "$VENV" -type f | wc -l | tr -d ' ')"
    echo "installed_distributions=$("$VENV/bin/python" - <<'PY'
import importlib.metadata as md
print(sum(1 for _ in md.distributions()))
PY
)"
  } > "$OUT/footprint.txt"
}

pip_audit() {
  "$PYTHON_BIN" -m venv "$AUDIT_VENV"
  "$AUDIT_VENV/bin/python" -m pip install pip-audit
  "$AUDIT_VENV/bin/pip-audit"     -r "$OUT/pip-audit-requirements.txt"     --format json     --output "$OUT/pip-audit.json"
}

apply_runtime_guard() {
  # Proxy-aware clients can reach only local loopback. This is a research guard,
  # not a kernel-level no-egress proof.
  export HTTP_PROXY="http://127.0.0.1:9"
  export HTTPS_PROXY="http://127.0.0.1:9"
  export ALL_PROXY="http://127.0.0.1:9"
  export http_proxy="$HTTP_PROXY"
  export https_proxy="$HTTPS_PROXY"
  export all_proxy="$ALL_PROXY"
  export NO_PROXY="127.0.0.1,localhost,::1"
  export no_proxy="$NO_PROXY"

  unset OPENAI_API_KEY ANTHROPIC_API_KEY DASHSCOPE_API_KEY GEMINI_API_KEY GOOGLE_API_KEY || true
  unset LANGCHAIN_API_KEY LANGSMITH_API_KEY || true
  export LANGCHAIN_TRACING_V2=false
  export LANGSMITH_TRACING=false
  export OLLAMA_MODEL_NAME="$OLLAMA_MODEL"
  export OLLAMA_HOST="$OLLAMA_HOST"
}

integration() {
  "$VENV/bin/python" "$DRIVER" integration     --repo-root "$ROOT"     --reme-bin "$VENV/bin/reme"     --config "$CONFIG"     --workspace "$WORKSPACE"     --model "$OLLAMA_MODEL"     --ollama-host "$OLLAMA_HOST"     --out "$OUT/integration"
}

printf 'Ada ReMe + LangMem final architecture characterization\n'
printf 'Results: %s\n\n' "$OUT"

critical preflight preflight
critical create-venv create_venv
critical install-runtime install_runtime
critical capture-runtime capture_runtime

# Security audit is evidence collection. A vulnerability finding must be reviewed
# but should not prevent the semantic/boundary characterization from running.
run_optional pip-audit pip_audit
cp "$OUT/logs/pip-audit.log" "$OUT/pip-audit.log" 2>/dev/null || true

apply_runtime_guard
critical integration integration
finish
