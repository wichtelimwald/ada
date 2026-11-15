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

network="none"
config_mount=""
if [ "$1" = "calendar-probe" ]; then
  if [ "$#" -ne 1 ]; then
    echo "error: calendar-probe takes its configuration from ADA_CALDAV_CONFIG" >&2
    exit 2
  fi
  : "${ADA_CALDAV_CONFIG:?Set ADA_CALDAV_CONFIG to the absolute pilot config file path}"
  case "${ADA_CALDAV_CONFIG}" in
    /*) ;;
    *) echo "error: ADA_CALDAV_CONFIG must be an absolute path" >&2; exit 2 ;;
  esac
  case "${ADA_CALDAV_CONFIG}" in
    *,*) echo "error: commas are unsupported in the config bind source" >&2; exit 2 ;;
  esac
  if [ ! -f "${ADA_CALDAV_CONFIG}" ]; then
    echo "error: CalDAV pilot configuration file does not exist" >&2
    exit 2
  fi
  config_mount="type=bind,src=${ADA_CALDAV_CONFIG},dst=/ada-config/caldav.json,readonly"
  case "${ADA_CALDAV_ALLOW_NETWORK:-0}" in
    0) ;;
    1) network="bridge" ;;
    *) echo "error: ADA_CALDAV_ALLOW_NETWORK must be 0 or 1" >&2; exit 2 ;;
  esac
  set -- calendar-probe --memory-root /ada-memory --config /ada-config/caldav.json
elif [ "${ADA_CALDAV_ALLOW_NETWORK:-0}" != "0" ]; then
  echo "error: provider network access is restricted to calendar-probe" >&2
  exit 2
fi

# Image identity: the label is a constant every branch build carries, and
# tags are mutable (smoke tests rebuild arbitrary working trees). Require the
# operator-recorded, full content-addressed ID of the reviewed build and run
# exactly that ID. Never derive this value from a tag at launch time.
: "${ADA_CREDENTIAL_IMAGE_ID:?Set ADA_CREDENTIAL_IMAGE_ID to the recorded sha256 ID of the reviewed credential image}"
image="${ADA_CREDENTIAL_IMAGE_ID}"
image_hex="${image#sha256:}"
case "${image}" in
  sha256:*) ;;
  *) echo "error: ADA_CREDENTIAL_IMAGE_ID must be a full sha256 image ID" >&2; exit 2 ;;
esac
case "${image_hex}" in
  ''|*[!0-9a-f]*) echo "error: ADA_CREDENTIAL_IMAGE_ID must be a full sha256 image ID" >&2; exit 2 ;;
esac
if [ "${#image_hex}" -ne 64 ]; then
  echo "error: ADA_CREDENTIAL_IMAGE_ID must be a full sha256 image ID" >&2
  exit 2
fi
inspected=$(docker image inspect \
  --format '{{.Id}} {{index .Config.Labels "org.ada.credential-runtime"}}' \
  "$image" 2>/dev/null) || {
  echo "error: recorded credential image ID is not present locally" >&2
  exit 2
}
if [ "$inspected" != "$image locked-aarch64-v1" ]; then
  echo "error: image is not the recorded reviewed credential-runtime build" >&2
  exit 2
fi

# Docker's DEFAULT PID mode creates a private namespace (do not pass
# --pid private: Docker rejects it; never use host/container sharing).
# Private PID namespace from container start closes the pre-opened same-UID
# /proc attack by other unprivileged workloads. Docker-host access remains
# a trusted operator boundary: docker exec / socket admin can bypass this.
# The operator-only CalDAV probe may explicitly opt in to bridge networking.
# Bridge is NOT an OS-level destination allowlist; trusted Ada's HTTP client
# restricts requests to the configured HTTPS origin. Never enable real
# credentials until the MVP-60 S6/S7 egress and review gates are satisfied.
# The vault and (only for the probe) config are individually mounted read-only.
set -- "$image" "$@"
if [ -n "$config_mount" ]; then
  set -- --mount "$config_mount" "$@"
fi
exec docker run --rm -it --pull never \
  --network "$network" \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=700,uid=10001,gid=10001 \
  --mount "type=bind,src=${ADA_MEMORY_ROOT}/secrets/ada.kdbx,dst=/ada-memory/secrets/ada.kdbx,readonly" \
  "$@"
