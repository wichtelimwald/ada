#!/bin/sh
set -u
OUT="$1"
FIXTURES="$2"
ROOT="$(git rev-parse --show-toplevel)"
mkdir -p "$OUT"
RUNTIME="$OUT/runtime"
STATUS="PASS"
NOTES="Reused the already-characterized full ReMe macOS harness with the common local model baseline."

if ! ADA_REME_SPIKE_ROOT="$RUNTIME" \
  REME_PREFERENCE_TOKEN="MEMCMP_PREF_5E39C2" \
  REME_CORRECTION_TOKEN="MEMCMP_CORR_A1D884" \
  REME_CONFLICT_TOKEN="MEMCMP_CONFLICT_C47B21" \
  REME_TOKEN_A="MEMCMP_ALPHA_PRIVATE_70B8D4" \
  REME_TOKEN_B="MEMCMP_BETA_PRIVATE_24E91A" \
  sh "$ROOT/research/memory/reme/mac/run.sh" >"$OUT/run.log" 2>&1; then
  if [ -f "$RUNTIME/steps.tsv" ] && grep -q '^preflight[[:space:]]\+FAIL' "$RUNTIME/steps.tsv"; then
    STATUS="BLOCKED"
    NOTES="ReMe target-Mac lane was blocked by a missing/unavailable prerequisite; inspect runtime/logs/preflight.log."
  else
    STATUS="FINDING"
    NOTES="ReMe comparison run reached characterization and had findings; inspect run.log. Existing prior characterization remains separate evidence."
  fi
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
