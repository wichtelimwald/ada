#!/bin/sh
# Target-only negative test: a tiny but authenticated synthetic KDBX4
# expands past the real credential runtime 1 GiB cgroup limit.
# No host vault mount, real credentials, network, or Docker socket.
set -eu

image="ada-credentials:locked"
label=$(docker image inspect \
  --format '{{index .Config.Labels "org.ada.credential-runtime"}}' \
  "$image")
if [ "$label" != "locked-aarch64-v1" ]; then
  echo "error: build the locked credential image first" >&2
  exit 2
fi

probe="ada-credential-oom-$$"
cleanup() { docker rm -f "$probe" >/dev/null 2>&1 || :; }
trap cleanup 0
trap 'exit 130' 2
trap 'exit 143' 15

# kdbxtool itself encrypts and HMAC-authenticates the synthetic payload.
# Only the test fixture creation replaces the GZIP output with a streaming
# compressed bomb. A fresh Python exec below removes the temporary patch.
# Actual reader/strict-process checks then run as PID 1 with the *production*
# cgroup memory limit. The OOM must be attributed to this specific container.
docker create --pull never --name "$probe" \
  --network none \
  --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=700,uid=10001,gid=10001 \
  --entrypoint python "$image" -I -c '
import gzip
import io
import os
import sys
from pathlib import Path
from unittest.mock import patch
from kdbxtool import Database
from kdbxtool.security import Argon2Config, KdfType

root = Path("/tmp/ada-oom-fixture")
(root / "secrets").mkdir(parents=True)
vault_path = root / "secrets" / "ada.kdbx"
compressed = io.BytesIO()
with gzip.GzipFile(fileobj=compressed, mode="wb", compresslevel=9) as stream:
    chunk = b"A" * 65536
    for _ in range(20_480):
        stream.write(chunk)
bomb = compressed.getvalue()
if len(bomb) >= 16 * 1024 * 1024:
    raise AssertionError("synthetic ciphertext fixture too large")
db = Database.create(
    password="synthetic-oom-master",
    kdf_config=Argon2Config(
        memory_kib=64 * 1024, iterations=32, parallelism=4,
        salt=os.urandom(32), variant=KdfType.ARGON2ID,
    ),
)
db.root_group.create_entry(
    title="ionos/calendar", password="synthetic-only-entry",
)
with patch("kdbxtool.parsing.kdbx4.gzip.compress", return_value=bomb):
    db.save(vault_path)
vault_path.chmod(0o600)
db.zeroize_credentials()
print(
    f"Synthetic authenticated KDBX4: {vault_path.stat().st_size} ciphertext bytes; "
    "1280 MiB decompressed payload",
    flush=True,
)
# In a fresh PID 1 interpreter, no patched library functions remain.
test_program = """
from ada.adapters.kdbx_secrets import KdbxSecrets, protect_credential_process
protect_credential_process()
print("Authenticated oversized KDBX4 unlock attempt started", flush=True)
with KdbxSecrets("/tmp/ada-oom-fixture") as vault:
    vault.unlock("synthetic-oom-master")
raise AssertionError("Oversized authenticated payload unexpectedly unlocked")
"""
os.execv(sys.executable, [sys.executable, "-I", "-c", test_program])
' >/dev/null

# docker start -a can return the application exit status. Capture it, then
# independently inspect Docker OOMKilled + ExitCode (not an incidental error).
set +e
docker start --attach "$probe"
start_status=$?
set -e
outcome=$(docker inspect --format '{{.State.OOMKilled}}/{{.State.ExitCode}}' "$probe")
if [ "$outcome" != "true/137" ]; then
  echo "error: expected container-scoped OOM kill, got $outcome (docker start: $start_status)" >&2
  exit 1
fi
echo "Authenticated oversized KDBX4 OOM contained by 1 GiB cgroup (exit 137)"
