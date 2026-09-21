#!/bin/sh
set -u
OUT="$1"
FIXTURES="$2"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
mkdir -p "$OUT/home" "$OUT/local-backend" "$OUT/npm"

STATUS="PASS"
NOTE="Letta local-backend/MemFS semantic lane completed."

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Node/npm unavailable."
else
  MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
  if [ "$MAJOR" -lt 22 ]; then
    STATUS="BLOCKED"
    NOTE="Letta Code requires Node >=22.19."
  fi
fi

if [ "$STATUS" = PASS ]; then
  npm install --prefix "$OUT/npm" "@letta-ai/letta-code@0.32.15" >"$OUT/install.log" 2>&1 || {
    STATUS="BLOCKED"
    NOTE="Letta Code npm install failed."
  }
fi

if [ "$STATUS" = PASS ]; then
  PROMPT_FILE="$OUT/prompt.txt"
  python3 - "$FIXTURES" "$PROMPT_FILE" <<'PY'
import json
import sys

f = json.load(open(sys.argv[1]))
text = f"""Synthetic Ada Memory comparison. Persist durable memory for each item using MemFS.
Keep evidence tokens verbatim. {f["instructions"]}

1) {f["preference"]}
2) {f["correction_before"]}
3) {f["correction_after"]}
4) {f["conflict_a"]}
5) {f["conflict_b"]}

Use human-readable Markdown memory files. Do not merely repeat the prompt; actually update persistent MemFS.
Final answer: MEMORY_COMPARE_DONE."""
open(sys.argv[2], "w").write(text)
PY

  export HOME="$OUT/home"
  export LETTA_LOCAL_BACKEND_EXPERIMENTAL=true
  export LETTA_LOCAL_BACKEND_DIR="$OUT/local-backend"
  export LETTA_CODE_DEV_PI_PROVIDER=ollama
  export OLLAMA_BASE_URL="http://127.0.0.1:11434/v1"
  export NO_PROXY="127.0.0.1,localhost,::1"

  "$OUT/npm/node_modules/.bin/letta"     -p "$(cat "$PROMPT_FILE")"     --yolo     --new-agent     --backend local     --base-tools none     --output-format text     -m "ollama/$MODEL"     >"$OUT/run.log" 2>&1 || {
      STATUS="FINDING"
      NOTE="Letta local semantic run failed; inspect run.log."
    }
fi

find "$OUT/local-backend" -type f -name '*.md' -print | sort |
while IFS= read -r f; do
  echo
  echo "===== ${f#$OUT/local-backend/} ====="
  cat "$f"
done > "$OUT/memfs-review.txt" 2>/dev/null || true

find "$OUT/local-backend" -type d -name .git -print |
while IFS= read -r g; do
  d="$(dirname "$g")"
  echo "===== $d ====="
  git -C "$d" status --short
  git -C "$d" log --oneline -10
done > "$OUT/git-review.txt" 2>/dev/null || true

cat > "$OUT/candidate.json" <<EOF
{"candidate":"letta","version":"0.32.15","status":"$STATUS","semantic_artifact":"letta/memfs-review.txt","substrate":{"authority":"Git-backed Markdown MemFS","rebuild":"Git/file-native; comparison captures repo state","forget":"NOT CHARACTERIZED in first semantic lane","isolation":"NOT CHARACTERIZED in first semantic lane"},"notes":["$NOTE","This lane focuses on MemFS semantic persistence; isolation/forget remain explicit follow-up if Letta survives semantics."]}
EOF
exit 0
