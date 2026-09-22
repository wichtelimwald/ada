#!/bin/sh
set -u

OUT="$1"
FIXTURES="$2"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
mkdir -p "$OUT/home" "$OUT/local-backend" "$OUT/npm" "$OUT/npm-cache"
export HOME="$OUT/home"
export NPM_CONFIG_CACHE="$OUT/npm-cache"

STATUS="PASS"
NOTE="Letta local-backend/MemFS semantic lane completed."

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  STATUS="BLOCKED"
  NOTE="Node/npm unavailable in the candidate sandbox."
else
  VERSION="$(node -p 'process.versions.node' 2>/dev/null || echo 0.0.0)"
  MAJOR="$(printf '%s' "$VERSION" | cut -d. -f1)"
  MINOR="$(printf '%s' "$VERSION" | cut -d. -f2)"
  if [ "$MAJOR" -lt 22 ] || { [ "$MAJOR" -eq 22 ] && [ "$MINOR" -lt 19 ]; }; then
    STATUS="BLOCKED"
    NOTE="Letta Code requires Node >=22.19; sandbox has $VERSION."
  fi
fi

if [ "$STATUS" = PASS ]; then
  npm install --prefix "$OUT/npm" "@letta-ai/letta-code@0.32.15" >"$OUT/install.log" 2>&1 || {
    STATUS="BLOCKED"
    NOTE="Letta Code npm install failed; inspect install.log."
  }
fi

if [ "$STATUS" = PASS ]; then
  PROMPT_FILE="$OUT/prompt.txt"
  node - "$FIXTURES" "$PROMPT_FILE" <<'JS'
const fs = require("fs");
const fixtures = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = process.argv[3];
const text = `Synthetic Ada Memory comparison. Persist durable memory for each item using MemFS.
Keep evidence tokens verbatim. ${fixtures.instructions}

1) ${fixtures.preference}
2) ${fixtures.correction_before}
3) ${fixtures.correction_after}
4) ${fixtures.conflict_a}
5) ${fixtures.conflict_b}

Use human-readable Markdown memory files. Do not merely repeat the prompt; actually update persistent MemFS.
Final answer: MEMORY_COMPARE_DONE.`;
fs.writeFileSync(out, text);
JS

  export LETTA_LOCAL_BACKEND_EXPERIMENTAL=true
  export LETTA_LOCAL_BACKEND_DIR="$OUT/local-backend"
  export LETTA_CODE_DEV_PI_PROVIDER=ollama
  export OLLAMA_BASE_URL
  export NO_PROXY="127.0.0.1,localhost,::1,host.docker.internal"
  export no_proxy="$NO_PROXY"

  "$OUT/npm/node_modules/.bin/letta" \
    -p "$(cat "$PROMPT_FILE")" \
    --yolo \
    --new-agent \
    --backend local \
    --base-tools none \
    --output-format text \
    -m "ollama/$MODEL" \
    >"$OUT/run.log" 2>&1 || {
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

if command -v git >/dev/null 2>&1; then
  find "$OUT/local-backend" -type d -name .git -print |
  while IFS= read -r g; do
    d="$(dirname "$g")"
    echo "===== $d ====="
    git -C "$d" status --short
    git -C "$d" log --oneline -10
  done > "$OUT/git-review.txt" 2>/dev/null || true
fi

ARTIFACT=""
[ -s "$OUT/memfs-review.txt" ] && ARTIFACT="letta/memfs-review.txt"

cat > "$OUT/candidate.json" <<EOF
{"candidate":"letta","version":"0.32.15","status":"$STATUS","semantic_artifact":"$ARTIFACT","substrate":{"authority":"Git-backed Markdown MemFS","rebuild":"Git/file-native; comparison captures repo state","forget":"NOT CHARACTERIZED in first semantic lane","isolation":"NOT CHARACTERIZED in first semantic lane"},"notes":["$NOTE","This lane focuses on MemFS semantic persistence; isolation/forget remain explicit follow-up if Letta survives semantics."]}
EOF
exit 0
