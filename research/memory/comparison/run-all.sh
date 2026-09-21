#!/bin/sh
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HERE="$ROOT/research/memory/comparison"
STAMP="$(date '+%Y%m%d-%H%M%S')"
OUT="${ADA_MEMORY_COMPARE_ROOT:-${TMPDIR:-/tmp}/ada-memory-compare-$STAMP}"
mkdir -p "$OUT/logs"

for candidate in reme langmem hindsight letta; do
  echo "==> $candidate"
  mkdir -p "$OUT/$candidate"
  if sh "$HERE/$candidate/run.sh" "$OUT/$candidate" "$HERE/fixtures.json" >"$OUT/logs/$candidate.log" 2>&1; then
    echo "    completed"
  else
    rc=$?
    echo "    runner finding (exit $rc; comparison continues)"
    tail -n 20 "$OUT/logs/$candidate.log" 2>/dev/null || true
    if [ ! -f "$OUT/$candidate/candidate.json" ]; then
      printf '{"candidate":"%s","status":"BLOCKED","semantic_artifact":"","substrate":{},"notes":["runner exited %s; see logs/%s.log"]}\n' "$candidate" "$rc" "$candidate" > "$OUT/$candidate/candidate.json"
    fi
  fi
done

python3 "$HERE/summarize.py" "$OUT"
echo "Result bundle: $OUT"
echo "Summary: $OUT/SUMMARY.md"
