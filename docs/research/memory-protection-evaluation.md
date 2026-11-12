# MVP-30 Memory protection mechanism evaluation

> **Historical research (scope superseded on 2026-11-12).** [ADR-0012](../decisions/ADR-0012-memory-access-mvp-boundary.md) removes Ada-managed encrypted vaults, per-person host isolation, and a separate Memory Broker from the MVP. Mechanism recommendations and remaining probes below are not current implementation gates. The native macOS evidence is retained in case a stronger future threat model warrants revisiting it.

Status: decision evidence for proposed ADR-0011  
Date: 2026-09-28

## Question

Which maintained mechanism should Ada adapt for encrypted, human-editable Memory
protection domains on the first supported macOS MVP, while keeping the broker and
domain semantics Ada-owned and avoiding unnecessary runtime dependencies?

This evaluates the protection/storage mechanism only. It does not delegate
authorization, Memory semantics, retrieval, or action authority to a third party.

## Requirements

A serious candidate must support or preserve:

- encryption at rest for each protection domain;
- ordinary human editing of Markdown while a domain is unlocked;
- no plaintext credential in repository/config/logs;
- no cloud service requirement;
- an Ada-owned request-scoped broker boundary;
- encrypted history as well as current Memory;
- restart/restore testing;
- a credible maintenance and license story;
- the current macOS MVP without unnecessarily closing a later Linux/server path.

## Candidates

| Candidate | License / platform | Evidence | Fit |
| --- | --- | --- | --- |
| macOS encrypted disk image behind an Ada adapter | Platform capability; no new redistributed dependency. Apple documents encrypted writable disk images and growable image formats; the current hdiutil man page documents AES-128/AES-256, stdin password input and SPARSEBUNDLE, while macOS 27 deprecates hdiutil in favor of diskutil image. Ada must therefore depend on a platform-vault adapter, not a command name. | https://support.apple.com/guide/disk-utility/dskutl11888/mac and https://keith.github.io/xcode-man-pages/hdiutil.1.html | **Best MVP control.** Native mounted filesystem keeps Markdown directly editable and avoids FUSE/Java/Python crypto dependencies. macOS-specific implementation must remain replaceable. |
| gocryptfs | MIT; current project status is mature on Linux, while macOS is explicitly described as beta quality and requires FUSE. The repository currently lists v2.6.1 as the latest changelog release. | https://github.com/rfjakob/gocryptfs | Strong Linux candidate later, but adds FUSE and a weaker macOS support posture than the platform capability. |
| CryFS | LGPL-3.0. The project still points to a stable 1.0 branch, but current 2.0 development is alpha/experimental, warns of data loss, and lists macOS as untested. | https://github.com/cryfs/cryfs | Do not choose for the macOS MVP: using the legacy stable line or the untested alpha line both create avoidable platform/maintenance risk. |
| Cryptomator Desktop | GPL-3.0 or commercial licensing for some integrations; mature end-user encrypted vault product, Java-based application. | https://github.com/cryptomator/cryptomator | Good user product, but too large a runtime/application dependency for Ada's narrow host-side broker primitive. |
| Cryptomator CLI / cryptofs | AGPL-3.0 or commercial dual licensing; Java filesystem provider. | https://github.com/cryptomator/cli and https://github.com/cryptomator/cryptofs | Technically relevant, but adds Java/runtime and stronger distribution obligations without solving Ada's authorization/broker semantics. |
| age | BSD-style 3-clause license; maintained simple file-encryption tool/library ecosystem. v1.3.2 was released on 2026-08-29 with Darwin arm64 binaries. | https://github.com/FiloSottile/age and https://github.com/FiloSottile/age/releases | Excellent candidate for exports/backups or envelope files, but it is file encryption rather than a directly editable mounted vault. Using it for every Markdown edit would require Ada to invent a plaintext-workspace lifecycle. |
| Whole-disk FileVault only | macOS platform feature. | https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac | Useful defense for the device but not a separate per-person/shared protection-domain boundary once the logged-in account can read everything. |

## Key storage

Apple Keychain is the first-platform control for small secrets. Apple's Keychain
Services documentation positions the keychain as encrypted storage for passwords,
keys and other small secrets, with access controls on macOS:

- https://developer.apple.com/documentation/security/keychain-services
- https://developer.apple.com/documentation/security/adding-a-password-to-the-keychain

For the command-line prototype, the macOS security tool supports generic password
items and application access restrictions. Broad allow-any-application access is
explicitly documented as insecure and must not be used:

- https://keith.github.io/xcode-man-pages/security.1.html

The exact Keychain access-control shape must be validated on the target Mac before
ADR-0011 can become Accepted. Secrets must be piped through standard input/API
memory, never placed in command arguments, environment variables, config files, or
logs.

## Git history implication

ADR-0010 currently stores .git below the human-editable Memory root. That is not
sufficient for MVP-30: repository-local Git config/attributes can affect command
execution, and Git objects contain historical plaintext.

The protected design therefore needs two independently controlled surfaces per
domain:

1. a human-editable encrypted current-Memory surface; and
2. broker-controlled encrypted history metadata/object storage that ordinary
   editors and sync tools cannot modify.

The implementation can still use Git behind the existing Ada adapter, but its
GIT_DIR must become separately configurable and protected while the current
working tree remains human-readable when unlocked.

## Multi-workspace concurrency evaluation

Separate human/editor and Ada Git workspaces would remove ADR-0010's final
same-working-tree publication race only if ordinary human edits participate in a
commit/synchronization protocol. Normal editors do not provide that contract by
themselves. Adding a watcher, auto-committer and merge/publish engine now would be a
second synchronization system, not a small protection-domain change.

Proposed MVP direction:

- retain MVP-20's optimistic revision checks for current Markdown in the first
  protection-domain implementation;
- keep the known late non-cooperating-save race explicit;
- do not claim Git worktrees/clones solve it until a concrete human-edit workflow
  is designed and tested;
- treat acceptance of that residual versus a stronger synchronization slice as an
  explicit ADR-0011 review decision before MVP-30 is marked done.

## Recommendation

For the first macOS MVP, adapt the platform encrypted-volume capability behind an
Ada-owned EncryptedVaultProvider boundary and use Keychain for per-domain secret
material. Do not make hdiutil itself architectural: use the currently supported
platform command only inside the adapter and retain a migration path to diskutil
image.

Do not add gocryptfs, CryFS, Cryptomator, age, or a Python crypto package to the
runtime for the live-vault problem at this stage. Re-evaluate gocryptfs or another
maintained provider when Linux/server deployment becomes an implemented
requirement. Re-evaluate age separately for backup/export if its simpler
file-encryption model fits that later slice.

## Native macOS isolation evidence retained from PR #47 (2026-11-12)

**Status:** research evidence only; not an accepted production architecture.
Original research/probe branch: [PR #47](https://github.com/wichtelimwald/ada/pull/47)
at commit [`5a0cca1`](https://github.com/wichtelimwald/ada/commit/5a0cca1bccf1d03b931568234f2006dfa41cdc8b).
Tests used **synthetic data** on the maintainer's target Mac (macOS 26.6.2,
arm64). Results below are recorded from maintainer-run PR comments, not
independently rerun in this documentation change.

| Probe | Observed result | What it demonstrates |
| --- | --- | --- |
| A: encrypted APFS vault | AES-256 sparse-bundle create/attach/detach/reattach, persistence and cleanup passed. Another process under the **same macOS user could read** the unlocked test file. Mounted root reported uid 501, gid 20, mode 0755. | Encryption at rest and process separation under one logged-in user **do not isolate unlocked plaintext** from that user's other processes. |
| B: different OS identity | The logged-in user could read the test vault and Keychain item. An existing restricted `nobody` identity could read neither: `vault_read_exit=1`, `keychain_read_exit=44`. Synthetic Keychain item, image and workspace were cleaned up. | Native macOS OS-user boundaries can deny those two accesses in the **tested configuration**; not a packaged Ada service or general proof. |
| C: local Unix peer credentials | With `getpeereid(3)` on a macOS Unix-domain stream socket, a connection from the wrong local UID was rejected **before payload processing**. The temporary restricted peer was accepted (`accepted_peer_uid=4294967294`) and completed synthetic `PING`; cleanup passed. | The tested **native macOS local socket** can authenticate a peer by kernel-supplied UID, not by caller-provided identity. This does **not** establish identity across Docker Desktop's Linux VM boundary. |

Primary observations: [Probe A](https://github.com/wichtelimwald/ada/pull/47#issuecomment-5883326260),
[Probe B denial](https://github.com/wichtelimwald/ada/pull/47#issuecomment-5920046554)
and [cleanup](https://github.com/wichtelimwald/ada/pull/47#issuecomment-5920057704),
[Probe C](https://github.com/wichtelimwald/ada/pull/47#issuecomment-6779919234).
The probe harness's **nine** regression tests passed at the cited PR head:
[exact-head test record](https://github.com/wichtelimwald/ada/pull/47#issuecomment-5925248723).
The failed first Probe C attempt and its diagnosis are also retained in
[PR #47](https://github.com/wichtelimwald/ada/pull/47#issuecomment-6779826213).

**Reproducibility/source:** exact research-only source files at that commit:
[`probe_encrypted_vault.py`](https://github.com/wichtelimwald/ada/blob/5a0cca1bccf1d03b931568234f2006dfa41cdc8b/research/memory/mvp-30-s2/probe_encrypted_vault.py),
[`probe_restricted_runtime.py`](https://github.com/wichtelimwald/ada/blob/5a0cca1bccf1d03b931568234f2006dfa41cdc8b/research/memory/mvp-30-s2/probe_restricted_runtime.py),
[`probe_ipc_peer_identity.py`](https://github.com/wichtelimwald/ada/blob/5a0cca1bccf1d03b931568234f2006dfa41cdc8b/research/memory/mvp-30-s2/probe_ipc_peer_identity.py)
and [harness tests](https://github.com/wichtelimwald/ada/blob/5a0cca1bccf1d03b931568234f2006dfa41cdc8b/tests/test_mvp30_s2_probe.py).
**Do not run the research README's obsolete optional Probe A `sudo -v` /
`--runtime-user` instructions.** Those commands do not match the code; see
[documented finding](https://github.com/wichtelimwald/ada/pull/47#issuecomment-6777692091).
No research script is copied into the production tree by this evidence record.

### Decision and remaining proof

The maintainer **rules out a dedicated Ada macOS system service**:
no additional non-login OS runtime account and no Ada-specific launchd system
daemon. The native restricted-user direction tested in PR #47 is **not selected**
for production. Retain the already accepted **container-first runtime**
([ADR-0003](../decisions/ADR-0003-execution-topology-containerization.md))
and scoped host-side Memory Broker
([ADR-0008](../decisions/ADR-0008-memory-architecture.md))
as the current design constraints; do not silently replace either.

A separate decision/probe is needed for a narrow container-to-host broker
connection, authenticated actor/audience binding, filesystem and Keychain
isolation **from the actual container**, and encryption of both current Memory
and Git history. A native `getpeereid(3)` result is not proof of a
container-to-host authentication mechanism. In particular, a remote Git
account does not protect a local checkout already available to the runtime.
The accepted ADR-0008 residual risk of a fully compromised runtime forging
trusted context is unchanged. **MVP-30 and ADR-0011 remain open.**

PR #47 also contains read-only evaluations of Octop (including a
[commit-pinned Memory backend inspection](https://github.com/wichtelimwald/ada/pull/47#issuecomment-6806187706)),
Hermes, OpenJarvis, Agent Wiki and Paperless-ngx
([comparison record](https://github.com/wichtelimwald/ada/pull/47#issuecomment-6780374557)).
Those are **research candidates, not adopted replacements**. The existing
Markdown/Git-authoritative Memory requirement in ADR-0008 is still accepted.
