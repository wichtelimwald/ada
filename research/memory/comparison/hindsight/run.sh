#!/bin/sh
set -u

OUT="$1"
FIXTURES="$2"
PYTHON_BIN="${PYTHON_BIN:-python3.14}"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
PORT="${HINDSIGHT_PORT:-28888}"
READY_TIMEOUT="${HINDSIGHT_READY_TIMEOUT:-420}"
DB_INSTANCE="${HINDSIGHT_DB_INSTANCE:-ada-memcmp-$PORT}"
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PID=""
mkdir -p "$OUT/home" "$OUT/data"
export HOME="$OUT/home"

cleanup() {
  [ -n "$PID" ] && kill "$PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

STATUS="PASS"
NOTE="Hindsight retain/recall, bank isolation, and document forget lane completed; reflect is an optional capability benchmark."

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Python 3.14 unavailable in the candidate sandbox."
else
  "$PYTHON_BIN" -m venv "$OUT/venv" >>"$OUT/install.log" 2>&1 || {
    STATUS="BLOCKED"
    NOTE="Hindsight virtual environment creation failed; inspect install.log."
  }

  if [ "$STATUS" = PASS ]; then
    "$OUT/venv/bin/python" -m pip install "hindsight-api-slim[embedded-db,local-onnx]==0.10.1" "hindsight-client==0.10.1" >>"$OUT/install.log" 2>&1 || {
      STATUS="BLOCKED"
      NOTE="Hindsight dependency installation failed; inspect install.log."
    }
  fi

  if [ "$STATUS" = PASS ]; then
    export HINDSIGHT_API_DATABASE_URL="pg0://$DB_INSTANCE"
    export HINDSIGHT_API_LLM_PROVIDER=ollama
    export HINDSIGHT_API_LLM_MODEL="$MODEL"
    export HINDSIGHT_API_LLM_BASE_URL="$OLLAMA_BASE_URL"
    export HINDSIGHT_API_LLM_OLLAMA_NUM_CTX=32768
    export HINDSIGHT_API_LLM_EXTRA_BODY='{"think": false}'
    export HINDSIGHT_API_EMBEDDINGS_PROVIDER=onnx
    export HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_ID="intfloat/multilingual-e5-small"
    export HINDSIGHT_API_RERANKER_PROVIDER=rrf
    export HINDSIGHT_API_ENABLE_RERANKING=false
    export HINDSIGHT_API_HOST="127.0.0.1"
    export HINDSIGHT_API_PORT="$PORT"

    "$OUT/venv/bin/hindsight-api" >"$OUT/server.log" 2>&1 &
    PID=$!
    "$OUT/venv/bin/python" "$HERE/driver.py" "http://127.0.0.1:$PORT" "$FIXTURES" "$OUT" "$READY_TIMEOUT" >"$OUT/run.log" 2>&1 || {
      STATUS="FINDING"
      NOTE="Hindsight core comparison lane did not complete; inspect semantic.json and run.log. Partial semantic evidence is preserved."
    }
  fi
fi

ARTIFACT=""
[ -f "$OUT/semantic.json" ] && ARTIFACT="hindsight/semantic.json"

cat > "$OUT/candidate.json" <<EOF
{"candidate":"hindsight","version":"0.10.1","status":"$STATUS","semantic_artifact":"$ARTIFACT","substrate":{"authority":"database memory bank","rebuild":"not file-source rebuild; bank/database is primary","forget":"document deletion exercised when lane completes","isolation":"native memory banks exercised when lane completes"},"notes":["$NOTE","This lane tests Hindsight as a derived learning/recall system, not as Ada's Markdown source of truth."]}
EOF
exit 0
