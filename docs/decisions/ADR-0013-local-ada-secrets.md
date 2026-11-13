# ADR-0013: Local, manually unlocked Ada credential vault

- **Status:** Accepted vault/unlock direction; optional KDBX reader PoC under review, no production integration
- **Date:** 2026-11-13
- **Decision owner:** Maintainer
- **Related:** [ADR-0003](ADR-0003-execution-topology-containerization.md), [ADR-0008](ADR-0008-memory-architecture.md), [ADR-0009](ADR-0009-calendar-provider-integration.md), [ADR-0012](ADR-0012-memory-access-mvp-boundary.md), [MVP-60](../plans/MVP-60-real-calendar-provider.md)

## Problem

Ada needs credentials for its own IONOS Mail Business account (calendar and later mail), potentially for third-party services such as Untis, including service-specific or user-linked accounts. The Ada process must not inherit broad access to the operator's personal macOS Keychain or password manager. The operator explicitly accepts **manual unlocking on every Ada start**, including after a crash/restart; unattended service recovery is not required.

The existing macOS Keychain IONOS probe is historical development evidence, not the credential architecture for the Ada runtime.

## Decision

1. **One dedicated KDBX credential vault for Ada only.** Maintain it using KeePassXC (an external operator tool). The encrypted `.kdbx` file lives persistently **within the configured Ada Memory storage area**, outside the container's writable layer, but is **not semantic Memory**. A single file in that storage area does not require an additional storage service, user, host Keychain bridge or protected vault process. The precise file path is an implementation detail.
2. **Master passphrase supplied interactively by the operator.** The KDBX master passphrase is never persisted, accepted via model/email messages, stored in environment variables, sent through command-line arguments or written to logs. No additional KeePass key file is required. A Docker container has no password to reuse: the requested password unlocks **the KDBX database**, through a trusted startup/unlock path, not through the model.
3. **Locked by default.** Without a successful operator unlock, credentials are unavailable and provider operations fail closed. Any container/application restart returns to locked state; **automatic unlocking and fully unattended restart are out of scope**. The exact interactive startup/unlock mechanism and its container lifecycle must be validated before real credentials are configured.
4. **Trusted runtime-only secret retrieval.** Ada's application/adapters request an explicitly configured secret reference; the model has no raw vault, passphrase or list-all-secrets tool. Secret references may live in trusted structured Ada configuration, not as grants learned from Memory. The operating process must never copy plaintext credentials into prompts, tool outputs, events, logging, durable DBOS inputs or indexes.
5. **Storage and history exclusion.** The KDBX file must never be treated as a Memory note, parsed/indexed for retrieval, added to model context or captured in Git Memory history. Before implementation, validate this against the actual `FileMemoryStore`/`GitMemoryHistory` behavior, ordinary and manual Git staging, backup/sync and restore. An explicit ignore/exclusion safeguard is needed, not merely an assumed filename convention. **Physical proximity to Memory does not make credentials Memory data.** No plaintext credentials or master keys may enter history.
6. **Blast-radius boundary (PoC unsafe for real secrets).** On the reviewed Docker Desktop/LinuxKit kernel, **another process with the same UID in the same container/PID namespace** could read both the **master passphrase** and decrypted entry passwords from an unlocked Ada process through `/proc/<pid>/mem`, despite `--cap-drop=ALL` and `no-new-privileges`. The master passphrase would also unlock **any accessible backup** of this vault, extending the damage beyond the live container. Read-only file mounts, Git exclusion and application-level secret allowlists do **not** defend against this. The optional VS Code Dev Container shares UID `ada` among the VS Code server, extensions, terminals, package-installed code and AI agents, and has network access: it is **synthetic-only**, not a credential-safe runtime. A compromised Ada process or dependency remains trusted with every credential in Ada's vault, even after OS hardening. The reader also retains decrypted Python strings after `lock()`; `zeroize_credentials()` does **not** securely erase all sensitive memory. Use of real credentials requires a dedicated restricted runtime, Linux `PR_SET_DUMPABLE=0` **before prompting**, early release of the reader's stored password/key material, a KDF-strength gate and a reviewed dependency lock; effectiveness must be tested on the actual platform. This reduces exposure, not guarantees complete process-memory erasure or host-level isolation. See [threat model](../security/threat-model.md).
7. **Backup and recovery.** The operator backs up the encrypted KDBX file and keeps the master passphrase recoverable independently. Failure to unlock must be visible; no silent fallback to another secret source. Credential rotation/revocation remains provider-specific.

## Alternatives and trade-off

- **macOS Keychain / Docker secret passthrough:** locally available, but introduces a host-credential bridge and platform coupling; the maintainer explicitly prefers not to grant Ada access to the personal Keychain.
- **1Password / Bitwarden / Keeper machine identities:** workable managed remote services with access controls, but add a cloud dependency/account-token bootstrap with little benefit for a small manually unlocked Ada-only credential set.
- **SOPS + age, pass/gopass:** viable local encrypted-file approaches, but require their own decryption-key bootstrap and are less convenient for the maintainer's interactive management preference.
- **KeePassXC/KDBX:** portable and local, with a well-defined encrypted format and a maintained graphical editor. Manual unlock costs availability after restarts but eliminates persistent runtime decryption credentials.

## Unresolved implementation gates

- **Library/license:** KDBX is a file format, not an automatic Python-library choice. KeePassXC CLI and PyKeePass are GPL-3.0; Python **kdbxtool 0.1.7 (Apache-2.0)** is used only for the opt-in PoC. It is **alpha**, with a single maintainer and limited adoption. On 2026-11-13 the maintainer reported a passing real KeePassXC open/reject smoke test and the exact-head Python 3.14 full suite (333 tests). This is **not** an audited production reader, source-security review or supply-chain approval. See [reader review](../research/kdbx-reader-evaluation.md).
- **Runtime unlock:** the opt-in local-chat path retains a manually unlocked vault **in its own running process**. The VS Code Dev Container is not isolated from same-UID processes and is explicitly **synthetic-only**, despite its read-only encrypted-file mount. The maintainer reported the standalone Docker smoke check passed; exact-head full-suite tests pass on Python 3.14, but a real runtime with credentials is neither implemented nor validated. It does not unlock a separate background process.
- **Persistence/authority:** verify non-indexing and Git exclusions, trusted secret-reference allowlist, missing/wrong password and locked-state denial, restart behavior, ciphertext backup and recovery with synthetic test entries.
- **Existing credential consumers:** update the MVP-60 calendar source, the D5 operation-fingerprint key source, and later MVP-70 mail, while preserving their existing no-secret-persistence requirements.

An experimental KDBX reader, one-shot interactive check and opt-in **same-process local-chat vault lifetime** have been staged in the ADR implementation PR. This is **not** the MVP-60 service composition root or a live-provider integration; no actual IONOS credentials or production-approved reader are available; an independent agent review reported B1/B2 documentation blockers and production-hardening gates, not a human security audit. No real secrets have been migrated.

## Revisit if

Ada must restart unattended; the number of credentials or required per-service isolation materially grows; credentials need remote/multi-host availability; or KDBX library compatibility/licensing proves unsuitable.

## Primary sources

- [KeePassXC documentation](https://keepassxc.org/docs/) (KDBX, passwords and key files)
- [KDBX 4.1 format specification](https://keepass.info/help/kb/kdbx.html)
- [PyKeePass package and license](https://pypi.org/project/pykeepass/) (GPL-3.0; selection still open)
