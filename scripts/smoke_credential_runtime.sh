#!/bin/sh
# Build and verify the isolated credential runtime without mounting any vault
# or using real credentials. Requires Docker Desktop on Linux/aarch64.
set -eu

# Also check the production launcher syntax (the Mac host may lack python).
sh -n scripts/run_ada_credentials.sh

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

# Docker creates a private PID namespace by default; --pid private is invalid.
# Do not use --pid host or --pid container:<id> here.
# Override the entrypoint for a synthetic-only runtime preflight.
# The application itself must report secure PID1, procfs, cgroup limits,
# -I Python flags, and read-only rootfs before any secret unlock.
docker run --rm --pull never \
  --network none \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=700,uid=10001,gid=10001 \
  --entrypoint python \
  "$image" -I -c \
  'from ada.adapters.kdbx_secrets import protect_credential_process; protect_credential_process(); print("Credential runtime isolation preflight passed (no vault mounted)")'

# In the same isolated profile, create/consume an entirely synthetic vault
# inside the container's ephemeral tmpfs. No host vault or other data is mounted.
# This exercises the ACTUAL configured 64 MiB / 51-round Argon2id KDBX4 path,
# rather than only inspecting a forged header.
docker run --rm --pull never \
  --network none \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=700,uid=10001,gid=10001 \
  --entrypoint python \
  "$image" -I -c '
import os
from pathlib import Path
from kdbxtool import Database
from kdbxtool.security import Argon2Config, KdfType
from ada.adapters.kdbx_secrets import (
    KdbxSecrets, SecretVaultError, protect_credential_process,
)

protect_credential_process()
root = Path("/tmp/ada-kdbx-smoke")
(root / "secrets").mkdir(parents=True)
path = root / "secrets" / "ada.kdbx"
db = Database.create(
    password="synthetic-only-master",
    kdf_config=Argon2Config(
        memory_kib=64 * 1024, iterations=51, parallelism=4,
        salt=os.urandom(32), variant=KdfType.ARGON2ID,
    ),
)
db.root_group.create_entry(
    title="ionos/calendar", username="synthetic@example.invalid",
    password="synthetic-only-entry",
)
db.save(path)
path.chmod(0o600)
db.zeroize_credentials()
vault = KdbxSecrets(root, allowed_entries=frozenset({"ionos/calendar"}))
try:
    vault.unlock("incorrect-synthetic-master")
except SecretVaultError:
    pass
else:
    raise AssertionError("Wrong passphrase accepted")
if vault.unlocked:
    raise AssertionError("Vault unlocked after wrong passphrase")
with vault:
    vault.unlock("synthetic-only-master")
    if vault.password("ionos/calendar") != "synthetic-only-entry":
        raise AssertionError("Synthetic KDBX4 lookup failed")
if vault.unlocked:
    raise AssertionError("Vault remained unlocked after exit")
print("Synthetic KDBX4 Argon2id unlock/lock passed (ephemeral tmpfs)")
'

# Negative early-open isolation regression: deliberately keep a synthetic,
# unprotected PID 1 alive before any prctl. A same-UID unprivileged sibling
# running in a SEPARATE default PID namespace must not see or open its /proc
# memory even during this pre-protection window. There is no vault mount,
# passphrase, network, Docker socket, or private data in either container.
probe_name="ada-credential-preopen-$$"
cleanup_preopen_probe() {
  docker rm -f "$probe_name" >/dev/null 2>&1 || :
}
trap cleanup_preopen_probe 0
trap 'exit 130' 2
trap 'exit 143' 15

docker run -d --rm --pull never --name "$probe_name" \
  --network none \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --entrypoint python "$image" -I -c '
import os, time
print(f"synthetic unprotected target pid={os.getpid()}", flush=True)
time.sleep(45)
' >/dev/null

ready=0
for attempt in 1 2 3 4 5; do
  if docker logs "$probe_name" 2>/dev/null |
      grep -qx "synthetic unprotected target pid=1"; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "error: synthetic pre-open target did not start as PID 1" >&2
  exit 2
fi

target_host_pid=$(docker inspect --format '{{.State.Pid}}' "$probe_name")
case "$target_host_pid" in
  ''|0|1|*[!0-9]*)
    echo "error: no valid target host PID for pre-open isolation test" >&2
    exit 2 ;;
esac

# The attacker knows the host PID (a stronger test than an ordinary sibling)
# but has neither the host PID namespace nor the Docker socket. Merely
# failing with EACCES would not prove namespace isolation: require ENOENT.
docker run --rm --pull never \
  --network none \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --entrypoint python "$image" -I -c '
import os, sys
from pathlib import Path

host_pid = sys.argv[1]
if os.getpid() != 1:
    raise AssertionError("attacker is not in its own private PID namespace")
if host_pid in os.listdir("/proc"):
    raise AssertionError("pre-protection target PID unexpectedly visible")
try:
    with (Path("/proc") / host_pid / "mem").open("rb"):
        raise AssertionError("unprotected target memory was opened")
except FileNotFoundError:
    print("Early pre-open /proc access denied by separate PID namespaces")
' "$target_host_pid"

cleanup_preopen_probe
trap - 0 2 15

echo "Image build, isolation, synthetic KDBX4 and early-preopen smoke tests passed."
