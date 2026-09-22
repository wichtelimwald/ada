#!/bin/sh
set -u

OUT="$1"
FIXTURES="$2"
PYTHON_BIN="${PYTHON_BIN:-python3.14}"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
mkdir -p "$OUT/home"
export HOME="$OUT/home"

STATUS="PASS"
NOTE="LangMem structured extraction/update completed against local Ollama."

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Python 3.14 not available in the candidate sandbox."
else
  "$PYTHON_BIN" -m venv "$OUT/venv" >>"$OUT/install.log" 2>&1 || {
    STATUS="BLOCKED"
    NOTE="LangMem virtual environment creation failed; inspect install.log."
  }

  if [ "$STATUS" = PASS ]; then
    "$OUT/venv/bin/python" -m pip install "langmem==0.0.30" "langchain-ollama==1.1.0" >>"$OUT/install.log" 2>&1 || {
      STATUS="BLOCKED"
      NOTE="LangMem dependency installation failed; inspect install.log."
    }
  fi

  if [ "$STATUS" = PASS ]; then
    HTTP_PROXY=http://127.0.0.1:9 \
    HTTPS_PROXY=http://127.0.0.1:9 \
    ALL_PROXY=http://127.0.0.1:9 \
    NO_PROXY=127.0.0.1,localhost,::1,host.docker.internal \
    no_proxy=127.0.0.1,localhost,::1,host.docker.internal \
      "$OUT/venv/bin/python" "$HERE/driver.py" "$FIXTURES" "$OUT" "$MODEL" "$OLLAMA_HOST" >"$OUT/run.log" 2>&1 || {
        STATUS="FINDING"
        NOTE="LangMem semantic run failed; inspect run.log."
      }
  fi
fi

ARTIFACT=""
[ -f "$OUT/semantic.json" ] && ARTIFACT="langmem/semantic.json"

cat > "$OUT/candidate.json" <<EOF
{"candidate":"langmem","version":"0.0.30","status":"$STATUS","semantic_artifact":"$ARTIFACT","substrate":{"authority":"caller-owned / storage-agnostic","rebuild":"N/A: caller store owns it","forget":"manager supports delete but disabled in semantic fixture; store-owned","isolation":"caller store/namespace-owned"},"notes":["$NOTE","This lane tests structured correction/contradiction semantics, not a Markdown persistence layer."]}
EOF
exit 0
