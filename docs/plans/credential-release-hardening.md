# Credential runtime release hardening — issue #58

Status: synthetic-only security hardening reviewed for merge (not approved for real credentials); see closure decision below.
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
  32,768 MiB-round bound and 512-iteration maximum passed synthetic
  KeePassXC production-launcher interoperability and bounded-KDF target
  benchmarks (see PR #60). No unlimited KDF.
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
  The security refresh pins PydanticAI 2.66.0, setuptools 84.1.0 and
  Debian zlib security patch. The operator reported successful rebuild,
  smoke and re-scan (205 matches / 60 High, down from 212 / 63).
  Full Python validation passed at exact HEAD `8d64507` (362 tests,
  10 skipped). The later macOS Docker smoke output did not print its
  Git SHA. Native artifact provenance, remaining OS advisories and
  binary redistribution obligations remain release-scope risks; hash
  pinning does not prove the absence of vulnerabilities.
- [ ] **KDBX reader safety:** source inspection confirms that upstream
  `kdbxtool 0.1.7` authenticates header and block HMACs **before**
  calling unbounded `gzip.decompress()`. The strict cgroup has a 1-GiB
  cap. The authenticated oversized-vault OOM test
  (`scripts/smoke_authenticated_oom.sh`) **passed on target 2026-11-15**:
  the 1,280 MiB expanded payload was contained by the 1-GiB cgroup
  (Docker OOMKilled=true/exit 137).
  Continue reviewing XML/protected fields, plaintext log/durability paths
  and Python memory-erasure limitations; document residual availability risk.
- [ ] **Acceptance and review:** target-Mac Docker builds and full test
  suite, synthetic KeePassXC interoperability, process isolation tests,
  incorrect-passphrase/locked-state denial, dependency lock verification.
  Independent security review with all merge-level findings closed. Then
  explicit maintainer merge authorization.

## Audit disposition for PR #60 — 2026-11-15

**MERGE SCOPE: offline, synthetic-only hardening code; no real credentials.**
Independent Claude agent review on `e19bba1` assessed all 49 pinned wheels,
native ELF surfaces and the full diff. Its merge-blocking findings #1
(image identity) and #3 (documentation) were fixed at `e858c69`,
`2be65b5` and `8d64507`; separate static re-review and exact-head
regression tests passed. This is an agent review, **not a human security
certification or a production credential authorization**.

**Residuals explicitly retained for the next operating/distribution gate:**

- **Native supply chain:** Grype does not inventory `psycopg-binary`'s
  bundled libpq/OpenSSL/Kerberos/LDAP and other ELF libraries, or all
  statically linked Rust libraries. The exact wheel contents were reviewed
  by the independent agent; full bundled-library CVE and redistribution/
  LGPL/NOTICE compliance is **not certified**. No prebuilt image is to be
  published; review before any DBOS/psycopg import in the credential process.
- **Unpatched Debian/CPython CVEs:** 205 Grype matches (60 High, no Critical);
  many are duplicate Debian package matches, not proof of runtime
  exploitability. The offline network-disabled, non-root process limits
  reachability; glibc/native risks remain. FIPS status was not measured,
  and CPython 3.14.11 is not yet published. Reassess before live egress.
- **KDBX availability/reader:** authenticated gzip is unbounded in
  `kdbxtool`; a target test established container-scoped OOM containment,
  not availability. Full reader security assurance is **not claimed**.
  The 1-lane worst-case Argon2 unlock benchmark remains unmeasured;
  bounded work may delay startup.
- **Image provenance/TCB:** the production launcher now requires an
  operator-recorded immutable image ID, but its actual end-to-end launch
  on that ID was not exercised after the change (fake-Docker regression
  tests and candidate smoke passed). `setuptools` executes its pinned
  `.pth` at startup; accepted for the synthetic-only stage, removable
  later if evidence justifies a multi-stage build. The macOS host, user
  account and Docker administrator are trusted by design.

**Decision:** These residuals do **not** block merging the synthetic-only
implementation. They **do** remain explicit gates for putting real
credentials in Ada, enabling provider network traffic, or distributing a
binary image. The maintainer approved merging only after this bounded
risk record; that is not blanket approval of later S6 operation.

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
