# Ada credential-bearing runtime — release candidate requirements

**State: release-hardening branch / issue #58, NOT APPROVED FOR REAL SECRETS.**
Implementation: `Dockerfile.credentials`, `scripts/run_ada_credentials.sh`,
`scripts/capture_ada_runtime_hashes.py`,
`scripts/check_credential_runtime_lock.py`.

This is one **Ada process**, not a new background secret service or custom
credential protocol. KDBX format + manually entered passphrase remain ADR-0013.
Cedar/AdaGuard covers authorization, not KDBX parsing or OS isolation.

## Why PR_SET_DUMPABLE alone is insufficient

The PR #59 independent reviewer reproduced that another same-UID process,
if already alive when Python starts, can open `/proc/<pid>/mem` before
`prctl(PR_SET_DUMPABLE,0)`; the descriptor remains readable later.
The guard denies *new* opens, not pre-opened descriptors.

**Primary defense:** start Ada directly as PID 1 in its **own private PID
namespace** in a dedicated container with no IDE, extensions, sidecars,
server or untrusted co-tenant. A different unprivileged container has no
access to this PID namespace by default. Docker **creates a private PID
namespace by default**; the launcher deliberately omits `--pid` (the
unsupported `--pid private` option caused the first smoke test to fail).
Neither launcher grants Docker socket access, host PID or privileged
capabilities. The credential image enables an additional code
check before prompting: Ada must be PID 1 and no other process may be
visible under `/proc`. A process enumeration snapshot is defense in depth,
not a solution to a namespace-sharing race.

**Trust boundary:** anyone who can control the Docker daemon/host, modify
the image before launch or run privileged `docker exec` is treated as
a privileged administrator. No Linux-only in-process flag can defend
against such an actor. The dedicated runtime must not be launched from
the VS Code Dev Container (which has other same-UID processes).
A read-only ciphertext mount is not process-memory isolation.

## Runtime launch policy

`scripts/run_ada_credentials.sh` is the only supported startup command
for the credential-bearing image. It requires an image with the reviewed
`org.ada.credential-runtime=locked-aarch64-v1` label and never accepts
another image name through arguments.

- Private PID namespace, user 10001, a single Ada foreground process;
  no `docker exec`, bind-mounted source code, writable host directories
  or shared PID namespace.
- Root filesystem read-only; only a 16 MiB `noexec,nosuid,nodev` /tmp
  tmpfs. Only the single **`ada.kdbx` file** is bind-mounted
  **read-only**; no other contents of the host's `secrets/` directory
  are exposed. The image contains an empty unreadable mount target.
- No network by default until MVP-60 S6 explicitly defines trusted
  IONOS/CalDAV egress. The current security release test is offline.
- `--memory=1g --memory-swap=1g` and a PID limit bound the memory
  blast radius of authenticated KDBX gzip expansion. An unexpectedly
  bloated vault may kill the Ada process; no provider write/retry may
  be misreported as successful after such a crash.
- Image sets `PYTHONNOUSERSITE=1`, starts `python -I -m ada`, and
  requires strict credential isolation checks. The strict Argon2 KDF
  budget requires at least 2,048 MiB-rounds and at most 8,192
  MiB-rounds, while preserving 64–256 MiB memory and 1–8 lanes.
  Benchmark this range before activating real vaults. No unrestricted
  Python plugin/extension loader is introduced.

Container memory and swap limits are mandatory **runtime configuration**.
An authenticated 65 KiB compressed vault expanded to 64 MiB in the
reviewer's test; the 16 MiB ciphertext cap alone cannot bound RAM.

## Supply chain and packaging

The seven KDBX-specific Linux/aarch64 wheels are already hash-pinned after
review. The *whole* Ada credential process includes PydanticAI, HTTP,
Cedar, DBOS and CalDAV dependencies: the reviewer counted 43 additional
distributions not covered by the seven-wheel lock.

**Captured on target (2026-11-14, maintainer supplied):** CPython 3.14.10
Linux/aarch64; pip's no-install report resolved exactly **49 packages** and
its `--require-hashes --dry-run` passed. The seven earlier reviewed KDBX
package hashes match exactly. The resulting 49-wheel candidate is committed
as `requirements/ada-runtime-py314-linux-aarch64.txt`. The Docker Desktop
`python:3.14-slim` local repository digest was reported as
`sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f`
and is pinned in `Dockerfile.credentials`. **A digest pin authenticates
identity, not the package's own security or native library provenance.**

Before building the credential image:

1. Re-run `python scripts/capture_ada_runtime_hashes.py` on the target
   CPython 3.14 Linux/aarch64 environment if dependency resolution is
   questioned: the script rejects any changed hash from the committed lock,
   requires the original seven KDBX digests to match and does not install
   packages or modify source files.
2. Verify the exact pinned base-image digest and its Linux/aarch64
   platform manifest, inspect relevant OS layers and current vulnerability
   advisories. Do not assume Docker Hub's `python:3.14-slim` tag remains
   stable; the digest pin remains explicit.
3. Build with that immutable base reference and check the resulting
   distribution inventory.
4. `Dockerfile.credentials` installs hash-verified **wheels only**, then
   builds Ada's local source offline with no dependency resolution or build
   isolation. `pip check` and an installed-distribution inventory
   check reject unreviewed extra packages.
5. Audit known vulnerabilities, exact native wheels/licenses and attribution
   for the *entire* graph, not merely versions and hashes. Keep the
   resulting evidence with the PR and NOTICE. Updates require a new
   reviewed lock and image build.

The full wheel lock and Docker base digest are now pinned. **No deployment
image is production-approved** until it builds on target, its installed
package inventory/OS layers and known vulnerabilities have been reviewed,
and the code and runtime isolation have passed independent assessment.

## Acceptance

- Genuine KeePassXC 2.8-created **synthetic** KDBX4/Argon2 vault at default
  calibrated settings unlocks, including early-release and wrong-passphrase
  denial. A weak/huge KDF is rejected before derivation; verify worst-case
  timing and memory in the same target container.
- Verify PID 1, sole visible process and non-dumpability. Reproduce the
  early-descriptor attack in the earlier shared-development environment;
  repeat with the private-runtime topology and demonstrate the unprivileged
  sibling cannot enter that namespace at process start. Late opens fail.
- Deliberately oversized *authenticated* gzip vault triggers contained
  failure (OOM or explicit denial) without host-wide resource exhaustion.
- Runtime image builds from the exact reviewed base digest and full wheel
  lock; distribution inventory and `pip check` pass. No secrets, credentials
  or personal events in logs, argv/env, model context or durable state.
- Full repository tests and independent security review pass. The maintainer
  separately approves merge and later real-credential activation.

**Not part of this security milestone:** CalDAV credential wiring, actual
IONOS authentication, sender/account identity or live egress. Those are
MVP-60 S6 after this release gate; they require their own end-to-end tests.
