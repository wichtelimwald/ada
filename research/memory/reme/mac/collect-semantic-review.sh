#!/bin/sh
set -eu

SRC="${1:-}"
OUT="${2:-/tmp/reme-semantic-review.txt}"

if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  echo "Usage: sh research/memory/reme/mac/collect-semantic-review.sh <llm-flow-result-dir> [output-file]" >&2
  exit 2
fi

: > "$OUT"

find "$SRC" -type f \( -name '*.md' -o -name '*.json' -o -name '*.jsonl' \) -print | sort |
while IFS= read -r f; do
  {
    echo
    echo "===== ${f#$SRC/} ====="
    cat "$f"
    echo
  } >> "$OUT"
done

echo "$OUT"
