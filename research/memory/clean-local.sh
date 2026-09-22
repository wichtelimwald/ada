#!/bin/sh
set -eu

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TARGET="$ROOT/.artifacts/research/memory"

if [ -d "$TARGET" ]; then
  rm -rf "$TARGET"
  echo "Removed repo-local Memory research artifacts: $TARGET"
else
  echo "No repo-local Memory research artifacts to remove."
fi

if [ "${1:-}" = "--legacy" ]; then
  for base in "${TMPDIR:-}" /tmp; do
    [ -n "$base" ] && [ -d "$base" ] || continue
    find "$base" -maxdepth 1 -type d \( -name 'ada-reme-spike-*' -o -name 'ada-memory-compare-*' \) -exec rm -rf {} + 2>/dev/null || true
  done
  rm -f /tmp/reme-semantic-review.txt 2>/dev/null || true
  echo "Removed legacy Ada Memory research artifacts from temporary directories."
fi
