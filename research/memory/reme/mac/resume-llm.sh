#!/bin/sh
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HARNESS_DIR="$ROOT/research/memory/reme/mac"
DRIVER="$HARNESS_DIR/driver.py"
RESULT_DIR="${1:-}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
PORT="${REME_PORT_A:-24331}"
BASE="http://127.0.0.1:$PORT"
PID=""

if [ -z "$RESULT_DIR" ]; then
  echo "Usage: sh research/memory/reme/mac/resume-llm.sh /path/to/ada-reme-spike-RESULT" >&2
  exit 2
fi

VENV="$RESULT_DIR/venv"
WORKSPACE="$RESULT_DIR/workspace-a"
OUT="$RESULT_DIR/llm-flow-retry"
LOG="$RESULT_DIR/logs/local-llm-memory-flow-retry.log"
SERVICE_LOG="$RESULT_DIR/logs/service-a-retry.log"

PREFERENCE_TOKEN="REME_PREF_RETRY_5E39C2"
CORRECTION_TOKEN="REME_CORRECTION_RETRY_A1D884"
CONFLICT_TOKEN="REME_CONFLICT_RETRY_C47B21"

stop_service() {
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
}
trap stop_service EXIT INT TERM

[ -x "$VENV/bin/reme" ] || {
  echo "Existing ReMe venv not found: $VENV" >&2
  exit 1
}
[ -d "$WORKSPACE" ] || {
  echo "Existing workspace not found: $WORKSPACE" >&2
  exit 1
}
command -v ollama >/dev/null 2>&1 || {
  echo "Ollama CLI not found" >&2
  exit 1
}
ollama show "$OLLAMA_MODEL" >/dev/null 2>&1 || {
  echo "Local model not available: $OLLAMA_MODEL" >&2
  exit 1
}
curl --fail --silent --show-error http://127.0.0.1:11434/api/tags >/dev/null

export HTTP_PROXY="http://127.0.0.1:9"
export HTTPS_PROXY="http://127.0.0.1:9"
export ALL_PROXY="http://127.0.0.1:9"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export all_proxy="$ALL_PROXY"
export NO_PROXY="127.0.0.1,localhost,::1"
export no_proxy="$NO_PROXY"

unset OPENAI_API_KEY ANTHROPIC_API_KEY DASHSCOPE_API_KEY GEMINI_API_KEY GOOGLE_API_KEY || true
export LLM_BACKEND="openai"
export LLM_MODEL_NAME="$OLLAMA_MODEL"
export LLM_API_KEY="ollama-local-research-only"
export LLM_BASE_URL="http://127.0.0.1:11434/v1"

mkdir -p "$OUT" "$RESULT_DIR/logs"

"$VENV/bin/reme" start \
  "workspace_dir=$WORKSPACE" \
  "service.host=127.0.0.1" \
  "service.port=$PORT" \
  "service.web_enabled=false" \
  "service.mcp_enabled=false" \
  "timezone=Europe/Berlin" \
  "language=en" \
  "enable_logo=false" \
  >"$SERVICE_LOG" 2>&1 &
PID=$!

if ! "$VENV/bin/python" "$DRIVER" wait --base-url "$BASE" --timeout 45 --out "$OUT/wait.json"; then
  echo "--- service log tail ---" >&2
  tail -n 60 "$SERVICE_LOG" >&2 || true
  exit 1
fi

if "$VENV/bin/python" "$DRIVER" llm \
  --base-url "$BASE" \
  --workspace "$WORKSPACE" \
  --date "$(date '+%Y-%m-%d')" \
  --preference-token "$PREFERENCE_TOKEN" \
  --correction-token "$CORRECTION_TOKEN" \
  --conflict-token "$CONFLICT_TOKEN" \
  --out "$OUT" \
  >"$LOG" 2>&1
then
  echo "PASS: local LLM Memory flow completed."
  echo "Artifacts: $OUT"
  exit 0
fi

echo "FAIL: local LLM Memory flow still failed." >&2
echo "--- driver log tail ---" >&2
tail -n 60 "$LOG" >&2 || true
echo "--- service log tail ---" >&2
tail -n 80 "$SERVICE_LOG" >&2 || true
exit 1
