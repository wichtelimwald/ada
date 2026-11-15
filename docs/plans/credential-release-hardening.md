# Credential runtime release hardening — issue #58

Status: implementation (not production-approved)
Baseline: merged PR #59, `cc9956c`
Owner: the current security hardening PR
Scope: **finish credential protection before MVP-60 S6**. No separate PoC or
CalDAV provider integration in this work.

## Goal and fixed design

Retain ADR-0013: one operator-managed KeePassXC KDBX vault, manual passphrase
entry at every startup, no Keychain bridge, no model-facing secret API.
Retain the already-integrated Python reader unless a concrete review finding
requires replacement. Cedar/AdaGuard controls **application authorization**,
not decrypting/storing the KDBX vault.

## Release gates

- [x] The synthetic KDBX PoC and first hardening pass are merged (#57, #59).
- [ ] **KeePassXC KDF interoperability:** support default calibrated Argon2
  vaults using a bounded total-work budget, with upper bounds on memory,
  iterations and lanes. Validate a real KeePassXC 2.8-created **synthetic**
  vault on the target Linux/aarch64 image. Never lower a real vault's KDF
  just to make it pass. **Maintainer decision 2026-11-14:** longer manual
  startup unlocks are acceptable. A 64 MiB / 406-iteration KeePassXC
  synthetic file was rejected by the former 8,192 MiB-round ceiling;
  a separate KDF benchmark took 7.93 s / 83 MiB peak RSS. The revised
  32,768 MiB-round bound and 512-iteration maximum are candidates pending
  exact-head real-launcher and ceiling-cost validation; no unlimited KDF.
- [ ] **Process isolation from startup:** dedicated single-process container,
  private PID namespace, non-root credential UID, no IDE/extensions or
  untrusted same-UID siblings, no arbitrary `docker exec`, no source bind
  mounts and no Docker socket. `PR_SET_DUMPABLE=0` is additional protection
  only against new ptrace/`/proc` opens. Validate the pre-open as well as
  late-open attack models; host/root remains trusted/out of scope.
- [ ] **Resource and egress controls:** bounded Docker memory and swap,
  read-only filesystem, non-root, cap-drop, no-new-privileges, PID/process
  limits. Start network-disconnected for offline synthetic unlock; define
  explicit allowed provider egress when MVP-60 S6 supplies the trusted
  composition. No credentials in the VS Code Dev Container.
- [ ] **Complete application supply chain:** **49** Linux/aarch64 CPython
  3.14 runtime/build wheel hashes and a fixed base digest are now committed.
  The target-side dry-run verification passed; the final Docker build,
  installed-inventory check, native wheel/OS layer vulnerability review,
  license attribution and shipped notices are **still outstanding**. Pinning
  hashes alone does not prove software safety.
- [ ] **KDBX reader safety:** source inspection confirms that upstream
  `kdbxtool 0.1.7` authenticates header and block HMACs **before**
  calling unbounded `gzip.decompress()`. The strict cgroup has a 1-GiB
  cap, but the authenticated oversized-vault OOM test
  (`scripts/smoke_authenticated_oom.sh`) is **not yet executed**.
  Continue reviewing XML/protected fields, plaintext log/durability paths
  and Python memory-erasure limitations; document residual availability risk.
- [ ] **Acceptance and review:** target-Mac Docker builds and full test
  suite, synthetic KeePassXC interoperability, process isolation tests,
  incorrect-passphrase/locked-state denial, dependency lock verification.
  Independent security review with all merge-level findings closed. Then
  explicit maintainer merge authorization.

## Non-goals

- Replacing the key store with Keychain/Vault/1Password.
- Reimplementing KDBX cryptography.
- Running live IONOS credentials or extending CalDAV (MVP-60 S6).
- Background auto-unlock or a bespoke secrets daemon.
- Treating a process-env switch or `PR_SET_DUMPABLE` alone as isolation.

## Success criterion

One reproducible, reviewed, offline-capable, private-PID credential runtime
using the full locked dependency graph and a bounded KeePassXC-compatible
reader. Provider wiring comes **only after** this gate. Live-provider egress
and end-to-end policy tests follow when S6 makes them meaningful.

## References

- ADR-0013: `docs/decisions/ADR-0013-local-ada-secrets.md`
- Attack evidence: PR #59 security review and `docs/security/threat-model.md`
- Issue #58 for closure, including the four remaining security gates.
