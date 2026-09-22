#!/bin/sh
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HERE="$ROOT/research/memory/comparison"
STAMP="$(date '+%Y%m%d-%H%M%S')"
BASE="$ROOT/artifacts/research/memory/comparison"
OUT="${ADA_MEMORY_COMPARE_ROOT:-$BASE/run-$STAMP}"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
DOCKER_OK=false

mkdir -p "$OUT/logs"
if [ -z "${ADA_MEMORY_COMPARE_ROOT:-}" ]; then
  mkdir -p "$BASE"
  ln -sfn "run-$STAMP" "$BASE/latest"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  DOCKER_OK=true
fi

write_blocked() {
  candidate="$1"
  note="$2"
  mkdir -p "$OUT/$candidate"
  CANDIDATE="$candidate" NOTE="$note" python3 - "$OUT/$candidate/candidate.json" <<'PY'
import json
import os
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "candidate": os.environ["CANDIDATE"],
            "status": "BLOCKED",
            "semantic_artifact": "",
            "substrate": {},
            "notes": [os.environ["NOTE"]],
        },
        indent=2,
    )
    + "\n"
)
PY
}

run_host_lane() {
  candidate="$1"
  echo "==> $candidate (target-Mac host characterization)"
  mkdir -p "$OUT/$candidate"
  if sh "$HERE/$candidate/run.sh" "$OUT/$candidate" "$HERE/fixtures.json" >"$OUT/logs/$candidate.log" 2>&1; then
    echo "    completed"
  else
    rc=$?
    echo "    runner finding (exit $rc; comparison continues)"
    tail -n 20 "$OUT/logs/$candidate.log" 2>/dev/null || true
    [ -f "$OUT/$candidate/candidate.json" ] || write_blocked "$candidate" "runner exited $rc; see logs/$candidate.log"
  fi
}

run_container_lane() {
  candidate="$1"
  image="$2"
  echo "==> $candidate (ephemeral sandbox container)"
  mkdir -p "$OUT/$candidate"

  if [ "$DOCKER_OK" != true ]; then
    echo "    BLOCKED: Docker is unavailable; no silent host fallback"
    write_blocked "$candidate" "Docker unavailable; candidate intentionally not executed unsandboxed on the host."
    return 0
  fi

  if docker run --rm \
    --cap-drop=ALL \
    --security-opt=no-new-privileges \
    --pids-limit=256 \
    --read-only \
    --tmpfs /tmp:rw,size=1024m \
    --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$ROOT,dst=/workspace,readonly" \
    --mount "type=bind,src=$OUT/$candidate,dst=/results" \
    --workdir /workspace \
    --env PYTHON_BIN=python3.14 \
    --env OLLAMA_MODEL="$MODEL" \
    --env OLLAMA_HOST=http://host.docker.internal:11434 \
    --env OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 \
    --env PIP_NO_CACHE_DIR=1 \
    "$image" \
    sh "/workspace/research/memory/comparison/$candidate/run.sh" \
      /results /workspace/research/memory/comparison/fixtures.json \
    >"$OUT/logs/$candidate.log" 2>&1
  then
    echo "    completed"
  else
    rc=$?
    echo "    runner finding (exit $rc; comparison continues)"
    tail -n 20 "$OUT/logs/$candidate.log" 2>/dev/null || true
    [ -f "$OUT/$candidate/candidate.json" ] || write_blocked "$candidate" "sandbox runner exited $rc; see logs/$candidate.log"
  fi
}

# ReMe's existing lane intentionally characterizes macOS/Apple Silicon itself.
run_host_lane reme

# New third-party candidates run outside the host process/filesystem by default.
run_container_lane langmem python:3.14-slim
run_container_lane hindsight python:3.14-slim
run_container_lane letta node:22-bookworm

python3 "$HERE/summarize.py" "$OUT"
echo "Result bundle: $OUT"
echo "Latest: $BASE/latest"
echo "Summary: $OUT/SUMMARY.md"
