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
6. **Blast-radius boundary.** A compromised, unlocked Ada process may read **all credentials in Ada's dedicated vault**. This design does not provide per-adapter isolation, but avoids giving Ada a general macOS Keychain interface or the operator's unrelated passwords. Separate stronger runtime isolation is a future decision only if required.
7. **Backup and recovery.** The operator backs up the encrypted KDBX file and keeps the master passphrase recoverable independently. Failure to unlock must be visible; no silent fallback to another secret source. Credential rotation/revocation remains provider-specific.

## Alternatives and trade-off

- **macOS Keychain / Docker secret passthrough:** locally available, but introduces a host-credential bridge and platform coupling; the maintainer explicitly prefers not to grant Ada access to the personal Keychain.
- **1Password / Bitwarden / Keeper machine identities:** workable managed remote services with access controls, but add a cloud dependency/account-token bootstrap with little benefit for a small manually unlocked Ada-only credential set.
- **SOPS + age, pass/gopass:** viable local encrypted-file approaches, but require their own decryption-key bootstrap and are less convenient for the maintainer's interactive management preference.
- **KeePassXC/KDBX:** portable and local, with a well-defined encrypted format and a maintained graphical editor. Manual unlock costs availability after restarts but eliminates persistent runtime decryption credentials.

## Unresolved implementation gates

- **Library/license:** KDBX is a file format, not an automatic Python-library choice. KeePassXC CLI and PyKeePass are GPL-3.0; Python **kdbxtool 0.1.7 (Apache-2.0)** is used only in an opt-in PoC container target. It is **alpha**, with limited adoption and unverified Python 3.14/KeePassXC interoperability. No production reader accepted. See [reader review](../research/kdbx-reader-evaluation.md).
- **Runtime unlock:** demonstrate a safe manual unlock in the actual container deployment without secrets in argv, env, Docker inspection output, process logs or chat; a naïve `docker exec` command in a separate process does not by itself unlock a different already-running Ada process.
- **Persistence/authority:** verify non-indexing and Git exclusions, trusted secret-reference allowlist, missing/wrong password and locked-state denial, restart behavior, ciphertext backup and recovery with synthetic test entries.
- **Existing credential consumers:** update the MVP-60 calendar source, the D5 operation-fingerprint key source, and later MVP-70 mail, while preserving their existing no-secret-persistence requirements.

An experimental KDBX reader and one-shot interactive CLI check have been staged in the ADR implementation PR. No live-runtime wiring, actual IONOS credentials, target-Mac compatibility test, or authorized reader for production is available. No real secrets have been migrated.

## Revisit if

Ada must restart unattended; the number of credentials or required per-service isolation materially grows; credentials need remote/multi-host availability; or KDBX library compatibility/licensing proves unsuitable.

## Primary sources

- [KeePassXC documentation](https://keepassxc.org/docs/) (KDBX, passwords and key files)
- [KDBX 4.1 format specification](https://keepass.info/help/kb/kdbx.html)
- [PyKeePass package and license](https://pypi.org/project/pykeepass/) (GPL-3.0; selection still open)
