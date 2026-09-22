#!/bin/sh
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HARNESS_DIR="$ROOT/research/memory/reme/mac"
DRIVER="$HARNESS_DIR/driver.py"
SPIKE_CONFIG="$HARNESS_DIR/spike-config.yaml"
PYTHON_BIN="${PYTHON_BIN:-python3.14}"
REME_VERSION="${REME_VERSION:-0.4.1.12}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
PORT_A="${REME_PORT_A:-24331}"
PORT_B="${REME_PORT_B:-24332}"
STAMP="$(date '+%Y%m%d-%H%M%S')"
RESULT_BASE="$ROOT/.artifacts/research/memory/reme"
RESULT_DIR="${ADA_REME_SPIKE_ROOT:-$RESULT_BASE/run-$STAMP}"
VENV="$RESULT_DIR/venv"
WORKSPACE_A="$RESULT_DIR/workspace-a"
WORKSPACE_B="$RESULT_DIR/workspace-b"
STEPS="$RESULT_DIR/steps.tsv"
BASE_A="http://127.0.0.1:$PORT_A"
BASE_B="http://127.0.0.1:$PORT_B"
PID_A=""
PID_B=""

OLD_TOKEN="${REME_OLD_TOKEN:-REME_OLD_4C8A72}"
NEW_TOKEN="${REME_NEW_TOKEN:-REME_EDITED_19F3D1}"
TOKEN_A="${REME_TOKEN_A:-ALPHA_PRIVATE_70B8D4}"
TOKEN_B="${REME_TOKEN_B:-BETA_PRIVATE_24E91A}"
PREFERENCE_TOKEN="${REME_PREFERENCE_TOKEN:-REME_PREF_3A6F11}"
CORRECTION_TOKEN="${REME_CORRECTION_TOKEN:-REME_CORRECTION_88C2D5}"
CONFLICT_TOKEN="${REME_CONFLICT_TOKEN:-REME_CONFLICT_61E7A9}"

mkdir -p "$RESULT_DIR/logs" "$WORKSPACE_A" "$WORKSPACE_B"\nif [ -z "${ADA_REME_SPIKE_ROOT:-}" ]; then\n  mkdir -p "$RESULT_BASE"\n  ln -sfn "run-$STAMP" "$RESULT_BASE/latest"\nfi
: > "$STEPS"

say() {
  printf '%s\n' "$*"
}

now_seconds() {
  date '+%s'
}

record() {
  name="$1"
  status="$2"
  seconds="$3"
  printf '%s\t%s\t%s\n' "$name" "$status" "$seconds" >> "$STEPS"
}

run_step() {
  name="$1"
  shift
  log="$RESULT_DIR/logs/$name.log"
  start="$(now_seconds)"
  say "==> $name"
  if "$@" >"$log" 2>&1; then
    end="$(now_seconds)"
    record "$name" PASS "$((end - start))"
    say "    PASS"
    return 0
  else
    rc=$?
    end="$(now_seconds)"
    record "$name" FAIL "$((end - start))"
    say "    FAIL (exit $rc; see $log)"
    say "    --- tail of log ---"
    tail -n 40 "$log" 2>/dev/null || true
    say "    --- end log tail ---"
    return "$rc"
  fi
}

finish_summary() {
  if command -v "$PYTHON_BIN" >/dev/null 2>&1 && [ -f "$DRIVER" ]; then
    "$PYTHON_BIN" "$DRIVER" summary --steps "$STEPS" --result-dir "$RESULT_DIR" || true
  else
    say "Results: $RESULT_DIR"
  fi
}

stop_pid() {
  pid="$1"
  [ -n "$pid" ] || return 0
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    i=0
    while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 20 ]; do
      sleep 0.25
      i=$((i + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  wait "$pid" 2>/dev/null || true
}

cleanup() {
  stop_pid "$PID_A"
  stop_pid "$PID_B"
}
trap cleanup EXIT INT TERM

critical() {
  name="$1"
  shift
  if ! run_step "$name" "$@"; then
    finish_summary
    exit 1
  fi
}

collect_environment() {
  {
    echo "timestamp=$(date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "repository=$ROOT"
    echo "branch=$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
    echo "head=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
    echo "uname=$(uname -a)"
    echo "os=$(sw_vers 2>/dev/null | tr '\n' ';' || true)"
    echo "arch=$(uname -m)"
    echo "python_bin=$PYTHON_BIN"
    "$PYTHON_BIN" --version
    echo "ollama_model=$OLLAMA_MODEL"
    ollama --version
  } > "$RESULT_DIR/environment.txt"
}

preflight() {
  [ "$(uname -s)" = "Darwin" ] || {
    echo "This characterization is intentionally scoped to macOS." >&2
    return 1
  }
  [ "$(uname -m)" = "arm64" ] || {
    echo "Expected Apple Silicon arm64; got $(uname -m)." >&2
    return 1
  }
  command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
    echo "Missing $PYTHON_BIN. The Ada target is Python 3.14; no automatic downgrade is allowed." >&2
    return 1
  }
  "$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info[:2] != (3, 14):
    raise SystemExit(f"Expected Python 3.14, got {sys.version}")
PY
  command -v curl >/dev/null 2>&1 || {
    echo "curl is required and is not installed." >&2
    return 1
  }
  command -v ollama >/dev/null 2>&1 || {
    echo "Ollama CLI is required and is not installed." >&2
    return 1
  }
  ollama show "$OLLAMA_MODEL" >/dev/null 2>&1 || {
    echo "Required local model is not present: $OLLAMA_MODEL" >&2
    echo "The spike deliberately does not download model artifacts automatically." >&2
    return 1
  }
  curl --fail --silent --show-error http://127.0.0.1:11434/api/tags >/dev/null
  collect_environment
}

create_venv() {
  "$PYTHON_BIN" -m venv "$VENV"
  "$VENV/bin/python" -m pip --version
}

install_reme() {
  "$VENV/bin/python" -m pip install "reme-ai[as]==$REME_VERSION"
  "$VENV/bin/python" -m pip check
  "$VENV/bin/python" - <<PY
import reme
if reme.__version__ != "$REME_VERSION":
    raise SystemExit(f"Expected ReMe $REME_VERSION, got {reme.__version__}")
print(reme.__version__)
PY
  "$VENV/bin/python" -m pip freeze > "$RESULT_DIR/pip-freeze.txt"
  "$VENV/bin/python" -m pip inspect --local > "$RESULT_DIR/pip-inspect.json"
  "$VENV/bin/python" - <<'PY' > "$RESULT_DIR/package-metadata.json"
import importlib.metadata as md
import json
rows = []
for dist in md.distributions():
    meta = dist.metadata
    rows.append({
        "name": meta.get("Name") or dist.name,
        "version": dist.version,
        "license_expression": meta.get("License-Expression"),
        "license": meta.get("License"),
        "home_page": meta.get("Home-page"),
        "project_urls": meta.get_all("Project-URL") or [],
    })
print(json.dumps(sorted(rows, key=lambda x: (x["name"] or "").lower()), indent=2))
PY
}

apply_runtime_network_guard() {
  # Soft guard only: it blocks ordinary proxy-aware HTTP clients from reaching
  # non-loopback destinations. It is not a kernel-level proof of zero egress.
  export HTTP_PROXY="http://127.0.0.1:9"
  export HTTPS_PROXY="http://127.0.0.1:9"
  export ALL_PROXY="http://127.0.0.1:9"
  export http_proxy="$HTTP_PROXY"
  export https_proxy="$HTTPS_PROXY"
  export all_proxy="$ALL_PROXY"
  export NO_PROXY="127.0.0.1,localhost,::1"
  export no_proxy="$NO_PROXY"

  unset OPENAI_API_KEY ANTHROPIC_API_KEY DASHSCOPE_API_KEY GEMINI_API_KEY GOOGLE_API_KEY || true
  unset LLM_API_KEY LLM_BASE_URL || true
  export OLLAMA_MODEL_NAME="$OLLAMA_MODEL"
  export OLLAMA_HOST="http://127.0.0.1:11434"
}

launch_service() {
  label="$1"
  workspace="$2"
  port="$3"
  log="$RESULT_DIR/logs/service-$label.log"
  "$VENV/bin/reme" start \
    "config=$SPIKE_CONFIG" \
    "workspace_dir=$workspace" \
    "service.host=127.0.0.1" \
    "service.port=$port" \
    "service.web_enabled=false" \
    "service.mcp_enabled=false" \
    "timezone=Europe/Berlin" \
    "language=en" \
    "enable_logo=false" \
    >"$log" 2>&1 &
  echo $!
}

snapshot_connections() {
  if ! command -v lsof >/dev/null 2>&1; then
    echo "lsof not available" > "$RESULT_DIR/network-connections.txt"
    return 0
  fi
  {
    echo "# ReMe A established TCP connections"
    lsof -nP -a -p "$PID_A" -iTCP -sTCP:ESTABLISHED 2>/dev/null || true
    if [ -n "$PID_B" ]; then
      echo "# ReMe B established TCP connections"
      lsof -nP -a -p "$PID_B" -iTCP -sTCP:ESTABLISHED 2>/dev/null || true
    fi
  } > "$RESULT_DIR/network-connections.txt"
}

say "Ada/ReMe macOS characterization spike"
say "Results are repo-local and git-ignored: $RESULT_DIR"
say "Pinned ReMe: $REME_VERSION"
say "Local model: $OLLAMA_MODEL"
say ""

critical preflight preflight
critical create-venv create_venv
critical install-reme install_reme
apply_runtime_network_guard
critical native-ollama-tool-probe "$VENV/bin/python" "$DRIVER" ollama-probe \
  --host "$OLLAMA_HOST" --model "$OLLAMA_MODEL" --out "$RESULT_DIR/native-ollama-tool-probe.json"

# C1/C3/C7: basic file path, retrieval, nested Ada metadata.
PID_A="$(launch_service a "$WORKSPACE_A" "$PORT_A")"
critical wait-a-initial "$PYTHON_BIN" "$DRIVER" wait --base-url "$BASE_A" --timeout 45 --out "$RESULT_DIR/wait-a-initial.json"
run_step basic-and-ada-metadata "$PYTHON_BIN" "$DRIVER" basic \
  --base-url "$BASE_A" --workspace "$WORKSPACE_A" --old-token "$OLD_TOKEN" --out "$RESULT_DIR/basic"
run_step status-one-workspace "$PYTHON_BIN" "$DRIVER" status --base-url "$BASE_A" --out "$RESULT_DIR/status-one-workspace.json"

# C3: stop, edit source out of band, remove derived metadata, restart, verify rebuilt search.
stop_pid "$PID_A"
PID_A=""
run_step outside-edit "$PYTHON_BIN" "$DRIVER" mutate --workspace "$WORKSPACE_A" --old-token "$OLD_TOKEN" --new-token "$NEW_TOKEN"
if [ -d "$WORKSPACE_A/metadata" ]; then
  mv "$WORKSPACE_A/metadata" "$RESULT_DIR/metadata-before-outside-rebuild"
fi
PID_A="$(launch_service a "$WORKSPACE_A" "$PORT_A")"
critical wait-a-after-edit "$PYTHON_BIN" "$DRIVER" wait --base-url "$BASE_A" --timeout 45 --out "$RESULT_DIR/wait-a-after-edit.json"
run_step rebuilt-search-after-outside-edit "$PYTHON_BIN" "$DRIVER" search \
  --base-url "$BASE_A" --query "$NEW_TOKEN" --contains "$NEW_TOKEN" --absent "$OLD_TOKEN" \
  --timeout 30 --out "$RESULT_DIR/search-after-outside-edit.json"

# C4: operational forget must survive a clean rebuild.
stop_pid "$PID_A"
PID_A=""
rm -f "$WORKSPACE_A/digest/wiki/ada-reme-spike-basic.md"
if [ -d "$WORKSPACE_A/metadata" ]; then
  mv "$WORKSPACE_A/metadata" "$RESULT_DIR/metadata-before-forget-rebuild"
fi
PID_A="$(launch_service a "$WORKSPACE_A" "$PORT_A")"
critical wait-a-after-forget "$PYTHON_BIN" "$DRIVER" wait --base-url "$BASE_A" --timeout 45 --out "$RESULT_DIR/wait-a-after-forget.json"
run_step forget-survives-rebuild "$PYTHON_BIN" "$DRIVER" search \
  --base-url "$BASE_A" --query "$NEW_TOKEN" --absent "$NEW_TOKEN" --timeout 30 \
  --out "$RESULT_DIR/search-after-forget.json"

# C5: two protection-domain workspaces in parallel.
PID_B="$(launch_service b "$WORKSPACE_B" "$PORT_B")"
critical wait-b "$PYTHON_BIN" "$DRIVER" wait --base-url "$BASE_B" --timeout 45 --out "$RESULT_DIR/wait-b.json"
run_step workspace-isolation "$PYTHON_BIN" "$DRIVER" isolation \
  --base-a "$BASE_A" --base-b "$BASE_B" --token-a "$TOKEN_A" --token-b "$TOKEN_B" \
  --out "$RESULT_DIR/isolation"
run_step status-workspace-a "$PYTHON_BIN" "$DRIVER" status --base-url "$BASE_A" --out "$RESULT_DIR/status-workspace-a.json"
run_step status-workspace-b "$PYTHON_BIN" "$DRIVER" status --base-url "$BASE_B" --out "$RESULT_DIR/status-workspace-b.json"

# C2/C6/C9: local LLM memory evolution. Semantic output is captured for review.
run_step local-llm-memory-flow "$PYTHON_BIN" "$DRIVER" llm \
  --base-url "$BASE_A" --workspace "$WORKSPACE_A" --date "$(date '+%Y-%m-%d')" \
  --preference-token "$PREFERENCE_TOKEN" --correction-token "$CORRECTION_TOKEN" \
  --conflict-token "$CONFLICT_TOKEN" --out "$RESULT_DIR/llm-flow"

snapshot_connections
finish_summary
say ""
say "Result bundle: $RESULT_DIR"
say "Primary summary: $RESULT_DIR/SUMMARY.md"
say "Machine-readable summary: $RESULT_DIR/summary.json"
say ""
say "Result bundle is under .artifacts/ and intentionally ignored by Git."
