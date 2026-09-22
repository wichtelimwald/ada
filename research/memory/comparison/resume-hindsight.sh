#!/bin/sh
set -eu

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HERE="$ROOT/research/memory/comparison"
RUN_DIR="${1:-$ROOT/artifacts/research/memory/comparison/latest}"
OUT="$RUN_DIR/hindsight"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"

if [ ! -d "$RUN_DIR" ] || [ ! -d "$OUT" ]; then
  echo "No existing comparison/Hindsight result found: $RUN_DIR" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker runtime is unavailable." >&2
  exit 2
fi

docker run --rm \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --read-only \
  --tmpfs /tmp:rw,size=1024m \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$ROOT,dst=/workspace,readonly" \
  --mount "type=bind,src=$OUT,dst=/results" \
  --workdir /workspace \
  --env PYTHON_BIN=python3.14 \
  --env OLLAMA_MODEL="$MODEL" \
  --env OLLAMA_HOST=http://host.docker.internal:11434 \
  --env OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 \
  --env HINDSIGHT_READY_TIMEOUT=420 \
  --env PIP_NO_CACHE_DIR=1 \
  python:3.14-slim \
  sh /workspace/research/memory/comparison/hindsight/run.sh \
    /results /workspace/research/memory/comparison/fixtures.json \
  >"$RUN_DIR/logs/hindsight.log" 2>&1

python3 "$HERE/summarize.py" "$RUN_DIR"
echo "Updated review bundle: $RUN_DIR/REVIEW-BUNDLE.txt"
