# ADR-0011: Memory Broker and protection-domain storage topology

- **Status:** Proposed
- **Date:** 2026-09-28

## Context

ADR-0008 selected a host-side Memory Broker and separate private/shared protection
domains. ADR-0010 made one local file-native root safer and added Git history, but
it intentionally left two issues to MVP-30:

1. a normal Ada runtime must not have standing access to every household vault;
2. human-editable current Memory and Git history need an enforceable encrypted
   protection boundary, including protection of Git metadata from untrusted editors
   and sync tools.

MVP-30 also has to bind broker access to trusted actor/audience/authorization
context without turning model output into authority.

The reuse evaluation is in
docs/research/memory-protection-evaluation.md.

## Proposed decision

### 1. Keep scope resolution broker-owned and fail closed

The Ada runtime sends a trusted MemoryAccessContext containing actor, audience,
authorization reference and requested storage operation. It does **not** send a
domain ID, filesystem path, encryption key, mount point, or provider credential.

The broker maps the exact context to a configured set of opaque protection-domain
IDs. Missing, mismatched, or ambiguous bindings fail closed. Domain IDs are
non-semantic opaque identifiers.

Constructing the context object is not authentication. The production broker
accepts it only over the trusted Ada application boundary defined by ADR-0008. A
fully compromised Ada runtime that can forge this trusted context remains an
accepted MVP residual threat; model/retrieved text must never be allowed to create
or modify it.

### 2. Run the production broker outside the ordinary Ada runtime

The production Memory Broker is a separate host-side process/service. The normal
Ada runtime receives scoped Memory operations/results, not all vault roots or
decryption material.

For the first local implementation, use a local-only IPC transport (Unix-domain
socket or equivalent platform-local transport) with restrictive filesystem
permissions. Do not open a TCP/network listener merely for convenience.

The exact message serialization is an implementation detail and must remain behind
the Ada-owned port.

#### Isolation boundary: research evidence and non-adopted native approach

**Decision update (2026-11-12): do not provision a separate Ada macOS
system service, dedicated non-login runtime user, or Ada-specific system
LaunchDaemon.** The maintainer explicitly ruled out that operating model.
This does not remove ADR-0008's approved host-side, request-scoped Memory
Broker; its production implementation and lifecycle are still undecided.
ADR-0003's accepted container-first runtime is the baseline.

Research-only [PR #47](https://github.com/wichtelimwald/ada/pull/47)
produced three target-Mac results, archived with sources in
[the Memory protection evaluation](../research/memory-protection-evaluation.md):

- **A:** AES-256 APFS encrypted-image operations passed, but a second
  **same-user native process read the unlocked plaintext**. A local process
  boundary alone is insufficient.
- **B:** the existing restricted `nobody` identity was denied access to a
  synthetic unlocked vault and synthetic user Keychain item. This proves a
  tested **native distinct-OS-identity** separation, not a production Ada
  service or a reason to install one.
- **C:** a local Unix-domain peer UID (`getpeereid(3)`) rejected a wrong UID
  before parsing the payload and admitted the expected test UID. This is
  **not a validated transport/authentication boundary across a Linux VM**.

The container-first deployment must not silently receive Memory mounts,
encryption keys, Keychain authority or a broad host-filesystem view.
Before production IPC or an encrypted-vault provider is implemented,
**re-evaluate and validate** the *actual* container-to-host broker access
model: transport across Docker Desktop's Linux VM, authenticating trusted
application context, fail-closed domain selection, permitted host resources,
negative cross-domain tests, and storage/history encryption. Do not assume
Unix-socket peer UID is transferable across that boundary. The fully
compromised runtime's context-forgery residual from ADR-0008 is unchanged.

**ADR-0011 remains Proposed.** The native probes settle useful mechanism
questions but do not constitute validation of the accepted runtime topology
or a final Memory-protection implementation.

### 3. Use one encrypted current-Memory vault per protection domain

On the first supported macOS MVP, adapt the platform encrypted-volume capability
behind an Ada-owned EncryptedVaultProvider. Current Markdown remains directly
human-editable while a domain is intentionally unlocked.

On current macOS 26, the platform probe may use encrypted AES-256 disk images via
hdiutil. The architecture does not depend on that binary: macOS 27 deprecates
hdiutil in favor of diskutil image, so command selection stays inside the adapter.

No cloud remote or sync service is implied by this choice.

### 4. Keep decryption secrets out of Memory and config

Per-domain vault secrets live in the platform credential store (Keychain on the
first macOS implementation) and are retrieved only by the broker/provider adapter.
They must not appear in Memory Markdown, Git, repository files, command arguments,
environment variables, logs, or model context.

The target-Mac implementation must validate restrictive Keychain access behavior.
It must not use broad allow-any-application access.

### 5. Separate human-editable current state from broker-controlled Git metadata

Each domain has a human-editable encrypted current-Memory surface and a separately
protected broker-controlled Git metadata/object surface. Ordinary editors and sync
tools must not be able to modify the Git configuration/attributes that Ada
executes.

GitMemoryHistory therefore needs a separately configurable GIT_DIR instead of
assuming <current-root>/.git. Both current Memory and history remain encrypted at
rest. Git remains recovery/versioning only, never authorization or current
semantic Memory.

### 6. Do not silently claim that Git multi-workspace synchronization solves human edits

Separate clones/worktrees were explicitly evaluated as required by MVP-30. They
only remove ADR-0010's final non-cooperating-save race if ordinary human edits
participate in a commit/synchronization protocol. Adding that protocol now would
introduce a second synchronization subsystem.

Before this ADR becomes Accepted, review must decide one of two explicit outcomes:

- accept the documented MVP residual late-save race for the initial protected
  current workspace; or
- add a separate synchronization slice with concrete commit ownership, conflict,
  offline and publish semantics.

No force reset/push or last-writer-wins reconciliation is allowed.

### 7. Keep source/document providers domain-scoped

The same opaque domain binding used for Memory will also select that domain's
source/document provider when those providers are introduced. A provider for one
domain must not widen another domain. This ADR does not define source retrieval
APIs ahead of the MVP-40 scenarios.

### 8. MemoryScope is not an authorization capability

`MemoryBrokerPort.resolve_scope()` returns `MemoryScope`/`ProtectionDomainRef`.
These are ordinary, caller-constructible Ada dataclasses so the S1 deterministic
test adapter can be exercised without a live broker process. That is safe only
because the invariant below is explicit and enforced, not merely assumed:

- `MemoryScope`/`ProtectionDomainRef` are broker-internal, non-authoritative
  metadata, never a bearer capability or proof of storage access;
- only broker-side code (the S1 `InMemoryMemoryBroker` test adapter, and the
  S2 production broker process behind the IPC boundary) may treat a resolved
  scope as authoritative;
- a future storage/provider operation (S2+) must re-present the trusted
  `MemoryAccessContext` to the broker boundary itself and receive a scoped
  operation/result from it, rather than accept a previously resolved
  `MemoryScope` or domain ID as sufficient proof of access. This matches the
  stronger statement in point 2 above that the ordinary runtime receives
  scoped Memory operations/results, not domain lists to act on directly.

`tests.test_architecture_boundaries` enforces the import boundary: no module
outside `ada.core.memory_access`, `ada.ports.memory_broker`, and
`ada.adapters.in_memory_memory_broker` may reference `MemoryScope` or
`ProtectionDomainRef`. This ADR does not yet define the S2+ storage-operation
API shape; that remains future work, deliberately out of S1 scope.

## Consequences

### Positive

- model output cannot select a broader vault by naming a domain/path;
- normal runtime code does not need all vault keys or roots;
- current Markdown remains directly inspectable/editable when unlocked;
- no new live-vault runtime dependency is required for the first macOS MVP;
- Git metadata can be protected from ordinary vault editors/sync tools;
- the storage backend remains replaceable for Linux/server deployment.

### Costs / limitations

- the first encrypted-vault provider is platform-specific;
- lock/unlock, mount cleanup, crash recovery and target-Mac behavior need explicit
  tests;
- a separate broker process and IPC boundary add operational surface;
- Keychain application-access behavior must be proven, not assumed;
- ADR-0010's final non-cooperating-save race is not resolved by S1 and remains a
  decision gate before MVP-30 completion;
- encrypted backup/restore is not complete until the detached-vault recovery slice
  is implemented and tested.

## Validation required before acceptance

- independent architecture/security review of the broker binding contract;
- a decided and validated **container-first** runtime-to-host-broker
  transport and authenticated scope binding, without introducing a dedicated
  macOS system daemon/account or exposing broad Memory roots/Keychain authority;
- negative tests from the **actual proposed runtime/container** proving no
  direct access to unrelated unlocked Memory domains or decryption secrets.
  The native PR #47 A/B/C probes are evidence, not substitutes for these tests;
- target-Mac encrypted vault create/unlock/lock/restart probe with synthetic data;
- proof that unrelated domains cannot be opened through normal broker requests;
- proof that the normal Ada runtime receives no key/root for an unrelated domain;
- proof that Git history is encrypted at rest and its configuration is not writable
  from the ordinary human-edit surface;
- detached encrypted backup/restore round-trip;
- explicit resolution of the concurrency residual above.

Until those checks pass, this ADR remains Proposed and MVP-30 remains not done.
