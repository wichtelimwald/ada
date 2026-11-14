#!/bin/sh
# Build and verify the isolated credential runtime without mounting any vault
# or using real credentials. Requires Docker Desktop on Linux/aarch64.
set -eu

image="ada-credentials:locked"
docker build --file Dockerfile.credentials --target credential-runtime \
  --tag "$image" .

label=$(docker image inspect \
  --format '{{index .Config.Labels "org.ada.credential-runtime"}}' \
  "$image")
if [ "$label" != "locked-aarch64-v1" ]; then
  echo "error: unexpected credential runtime image label" >&2
  exit 2
fi

# Override the entrypoint for a synthetic-only runtime preflight.
# The application itself must report secure PID1, procfs, cgroup limits,
# -I Python flags, and read-only rootfs before any secret unlock.
docker run --rm --pull never \
  --pid private --network none \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=700,uid=10001,gid=10001 \
  --entrypoint python \
  "$image" -I -c \
  'from ada.adapters.kdbx_secrets import protect_credential_process; protect_credential_process(); print("Credential runtime isolation preflight passed (no vault mounted)")'

echo "Image build and no-credential runtime preflight passed."
