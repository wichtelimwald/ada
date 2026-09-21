#!/bin/sh
set -u
OUT="$1"
FIXTURES="$2"
ROOT="$(git rev-parse --show-toplevel)"
mkdir -p "$OUT"
RUNTIME="$OUT/runtime"
STATUS="PASS"
NOTES="Reused the already-characterized full ReMe macOS harness with the common local model baseline."

if ! ADA_REME_SPIKE_ROOT="$RUNTIME" sh "$ROOT/research/memory/reme/mac/run.sh" >"$OUT/run.log" 2>&1; then
  STATUS="FINDING"
  NOTES="ReMe comparison run had findings; inspect run.log. Existing prior characterization remains separate evidence."
fi
if [ -d "$RUNTIME/llm-flow" ]; then
  sh "$ROOT/research/memory/reme/mac/collect-semantic-review.sh" "$RUNTIME/llm-flow" "$OUT/semantic-review.txt" >/dev/null 2>&1 || true
fi
cat > "$OUT/candidate.json" <<EOF
{
  "candidate": "reme",
  "version": "0.4.1.12",
  "status": "$STATUS",
  "semantic_artifact": "reme/semantic-review.txt",
  "substrate": {
    "authority": "Markdown/YAML files",
    "rebuild": "native; clean metadata rebuild characterized",
    "forget": "native current-state deletion characterized",
    "isolation": "separate workspaces characterized"
  },
  "notes": ["$NOTES", "Known baseline finding: generated correction metadata/digest can contradict the corrected Markdown body."]
}
EOF
exit 0
