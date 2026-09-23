#!/bin/sh
set -eu

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DEST="$ROOT/artifacts/research/memory/legacy"
mkdir -p "$DEST"

moved=0

move_matches() {
  base="$1"
  [ -n "$base" ] && [ -d "$base" ] || return 0

  find "$base" -maxdepth 1 -type d \( -name 'ada-reme-spike-*' -o -name 'ada-memory-compare-*' \) -print |
  while IFS= read -r src; do
    name="$(basename "$src")"
    target="$DEST/$name"
    if [ -e "$target" ]; then
      echo "Already present, leaving source unchanged: $target"
      continue
    fi
    mv "$src" "$target"
    echo "Moved: $src -> $target"
  done
}

move_matches "${TMPDIR:-}"
move_matches /tmp

if [ -f /tmp/reme-semantic-review.txt ]; then
  target="$DEST/reme-semantic-review.txt"
  if [ ! -e "$target" ]; then
    mv /tmp/reme-semantic-review.txt "$target"
    echo "Moved: /tmp/reme-semantic-review.txt -> $target"
  fi
fi

echo "Legacy Memory research artifacts are now under: $DEST"
echo "Note: moved virtual environments are kept only as evidence and should not be resumed after relocation."
