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
  just to make it pass.
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
- [ ] **Complete application supply chain:** a *single* Linux/aarch64
  CPython 3.14 hash lock covers all Ada runtime dependencies, KDBX and
  PEP 517 build requirements, rather than just seven KDBX wheels. Build
  without source distributions or new unreviewed download paths; pin the
  base image digest and run `pip check` plus inventory diff. Review
  licenses, native libraries, wheel contents, known vulnerabilities and
  the shipped third-party notices. No guarantees from hashes alone.
- [ ] **KDBX reader safety:** focused source review of KDBX4 authenticated
  processing, KDF parsing, post-authenticated gzip expansion/oom, XML and
  protected-field handling; enforce container memory cap, no plaintext in
  logs/durable storage, no key material after exit. Remaining Python memory
  erasure limitations must be explicit and accepted.
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
