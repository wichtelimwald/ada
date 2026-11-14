#!/bin/sh
# Trusted Mac-side launcher for the future reviewed, hash-locked Ada runtime.
# Until the credential release gate passes, use SYNTHETIC vault data only.
set -eu

: "${ADA_MEMORY_ROOT:?Set ADA_MEMORY_ROOT to the operator-controlled vault root}"
case "${ADA_MEMORY_ROOT}" in
  /*) ;;
  *) echo "error: ADA_MEMORY_ROOT must be an absolute path" >&2; exit 2 ;;
esac
case "${ADA_MEMORY_ROOT}" in
  *,*) echo "error: commas are unsupported in the bind-mount source" >&2; exit 2 ;;
esac
if [ ! -f "${ADA_MEMORY_ROOT}/secrets/ada.kdbx" ]; then
  echo "error: Ada KDBX file does not exist" >&2
  exit 2
fi
if [ "$#" -eq 0 ]; then
  set -- secrets-check --memory-root /ada-memory
fi

# This exact locally built target must carry the label from the reviewed
# Dockerfile credential-runtime stage. An arbitrary development image is denied.
image="ada-credentials:locked"
actual_label=$(docker image inspect \
  --format '{{index .Config.Labels "org.ada.credential-runtime"}}' \
  "$image" 2>/dev/null) || {
  echo "error: build the reviewed hash-locked credential image first" >&2
  exit 2
}
if [ "$actual_label" != "locked-aarch64-v1" ]; then
  echo "error: image is not the reviewed credential-runtime build target" >&2
  exit 2
fi

# Docker's DEFAULT PID mode creates a private namespace (do not pass
# --pid private: Docker rejects it; never use host/container sharing).
# Private PID namespace from container start closes the pre-opened same-UID
# /proc attack by other unprivileged workloads. Docker-host access remains
# a trusted operator boundary: docker exec / socket admin can bypass this.
# Offline-only until MVP-60 S6 defines and validates provider network egress.
# Mount ONLY the KDBX file, not the whole secrets directory: least privilege.
exec docker run --rm -it --pull never \
  --network none \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=700,uid=10001,gid=10001 \
  --mount "type=bind,src=${ADA_MEMORY_ROOT}/secrets/ada.kdbx,dst=/ada-memory/secrets/ada.kdbx,readonly" \
  "$image" "$@"
