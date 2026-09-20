#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
PYTHON=${PYTHON:-"$ROOT/.venv/bin/python"}
if [ ! -x "$PYTHON" ]; then
  PYTHON=${PYTHON_FALLBACK:-python3}
fi

DUCKLING_COMMIT=59a13ff87b1aa8be6b93d387244f8636b26185c5
TMP=$(mktemp -d "${TMPDIR:-/tmp}/ada-duckling-characterization.XXXXXX")
NAME="ada-duckling-characterization-$$"
IMAGE="ada-duckling-characterization:${DUCKLING_COMMIT}"
PORT=18000

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap cleanup EXIT HUP INT TERM

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: Docker is not installed; Duckling characterization not run." >&2
  exit 2
fi

if ! docker info >/dev/null 2>&1; then
  echo "SKIP: Docker daemon is not available; Duckling characterization not run." >&2
  exit 2
fi

echo "==> duckling: clone pinned upstream source"
git clone -q https://github.com/facebook/duckling.git "$TMP/duckling"
git -C "$TMP/duckling" checkout -q "$DUCKLING_COMMIT"

echo "==> duckling: build pinned upstream Dockerfile"
docker build -q -t "$IMAGE" "$TMP/duckling" >/dev/null

echo "==> duckling: start loopback-only service"
docker run -d --rm --name "$NAME" -p "127.0.0.1:${PORT}:8000" "$IMAGE" >/dev/null

ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if "$PYTHON" -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:${PORT}/', timeout=1).read().decode())" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "FAIL: Duckling service did not become ready." >&2
  docker logs "$NAME" >&2 || true
  exit 1
fi

echo "==> duckling: characterize"
"$PYTHON" "$HERE/run_duckling_characterization.py" --base-url "http://127.0.0.1:${PORT}"
