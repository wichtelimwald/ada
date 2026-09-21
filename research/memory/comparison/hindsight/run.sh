#!/bin/sh
set -u
OUT="$1"
FIXTURES="$2"
PYTHON_BIN="${PYTHON_BIN:-python3.14}"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
PORT="${HINDSIGHT_PORT:-28888}"
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PID=""
mkdir -p "$OUT/home" "$OUT/data"

cleanup() {
  [ -n "$PID" ] && kill "$PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

STATUS="PASS"
NOTE="Hindsight retain/recall/reflect, bank isolation, and document forget lane completed."

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Python 3.14 unavailable."
elif ! command -v ollama >/dev/null 2>&1 || ! ollama show "$MODEL" >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Required local Ollama model unavailable."
else
  "$PYTHON_BIN" -m venv "$OUT/venv" >>"$OUT/install.log" 2>&1 || STATUS="BLOCKED"
  if [ "$STATUS" = PASS ]; then
    "$OUT/venv/bin/python" -m pip install "hindsight-api-slim[embedded-db,local-onnx]==0.10.1" "hindsight-client==0.10.1" >>"$OUT/install.log" 2>&1 || STATUS="BLOCKED"
  fi
  if [ "$STATUS" = PASS ]; then
    export HOME="$OUT/home"
    export HINDSIGHT_API_DATABASE_URL="pg0://ada-memcmp-$PORT"
    export HINDSIGHT_API_LLM_PROVIDER=ollama
    export HINDSIGHT_API_LLM_MODEL="$MODEL"
    export HINDSIGHT_API_LLM_BASE_URL="http://127.0.0.1:11434/v1"
    export HINDSIGHT_API_LLM_OLLAMA_NUM_CTX=32768
    export HINDSIGHT_API_LLM_EXTRA_BODY='{"think": false}'
    export HINDSIGHT_API_EMBEDDINGS_PROVIDER=onnx
    export HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_ID="intfloat/multilingual-e5-small"
    export HINDSIGHT_API_RERANKER_PROVIDER=rrf
    export HINDSIGHT_API_ENABLE_RERANKING=false
    export HINDSIGHT_API_HOST="127.0.0.1"\n    export HINDSIGHT_API_PORT="$PORT"

    "$OUT/venv/bin/hindsight-api" >"$OUT/server.log" 2>&1 &
    PID=$!
    "$OUT/venv/bin/python" "$HERE/driver.py" "http://127.0.0.1:$PORT" "$FIXTURES" "$OUT" >"$OUT/run.log" 2>&1 || {
      STATUS="FINDING"
      NOTE="Hindsight comparison lane failed; inspect server.log/run.log. First startup may need the local ONNX model download."
    }
  fi
fi

cat > "$OUT/candidate.json" <<EOF
{"candidate":"hindsight","version":"0.10.1","status":"$STATUS","semantic_artifact":"hindsight/semantic.json","substrate":{"authority":"database memory bank","rebuild":"not file-source rebuild; bank/database is primary","forget":"document deletion exercised","isolation":"native memory banks exercised"},"notes":["$NOTE","This lane tests Hindsight as a derived learning/recall system, not as Ada's Markdown source of truth."]}
EOF
exit 0
