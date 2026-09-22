#!/bin/sh
set -eu

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SRC="${1:-}"
OUT="${2:-$ROOT/.artifacts/research/memory/reviews/reme-semantic-review.txt}"

if [ -z "$SRC" ]; then
  RUN="$ROOT/.artifacts/research/memory/reme/latest"
  if [ -d "$RUN" ]; then
    SRC="$(find "$RUN" -maxdepth 1 -type d -name 'llm-flow-retry-*' -print | sort | tail -n 1)"
    [ -n "$SRC" ] || SRC="$RUN/llm-flow"
  fi
fi

if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  echo "No ReMe semantic result found. Run the characterization first or pass an explicit llm-flow directory." >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"
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
