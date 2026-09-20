#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
IMAGE="ada-context-research:tmp-$$"

cleanup() {
  docker image rm -f "$IMAGE" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

docker build \
  --no-cache \
  --progress=plain \
  --build-arg "VERBOSE=${VERBOSE:-0}" \
  --tag "$IMAGE" \
  --file "$HERE/Dockerfile.research" \
  "$HERE"
