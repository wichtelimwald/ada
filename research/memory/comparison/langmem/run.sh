#!/bin/sh
set -u
OUT="$1"
FIXTURES="$2"
PYTHON_BIN="${PYTHON_BIN:-python3.14}"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
mkdir -p "$OUT"
STATUS="PASS"
NOTE="LangMem structured extraction/update completed against local Ollama."

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Python 3.14 not available."
elif ! command -v ollama >/dev/null 2>&1 || ! ollama show "$MODEL" >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Required local Ollama model unavailable."
else
  "$PYTHON_BIN" -m venv "$OUT/venv" >>"$OUT/install.log" 2>&1 || STATUS="BLOCKED"
  if [ "$STATUS" = PASS ]; then
    "$OUT/venv/bin/python" -m pip install "langmem==0.0.30" "langchain-ollama==1.1.0" >>"$OUT/install.log" 2>&1 || STATUS="BLOCKED"
  fi
  if [ "$STATUS" = PASS ]; then
    HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 NO_PROXY=127.0.0.1,localhost,::1       "$OUT/venv/bin/python" "$HERE/driver.py" "$FIXTURES" "$OUT" "$MODEL" >"$OUT/run.log" 2>&1 || {
        STATUS="FINDING"
        NOTE="LangMem semantic run failed; inspect run.log."
      }
  fi
fi

cat > "$OUT/candidate.json" <<EOF
{"candidate":"langmem","version":"0.0.30","status":"$STATUS","semantic_artifact":"langmem/semantic.json","substrate":{"authority":"caller-owned / storage-agnostic","rebuild":"N/A: caller store owns it","forget":"manager supports delete but disabled in semantic fixture; store-owned","isolation":"caller store/namespace-owned"},"notes":["$NOTE","This lane tests structured correction/contradiction semantics, not a Markdown persistence layer."]}
EOF
exit 0
