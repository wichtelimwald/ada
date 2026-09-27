# MVP-30 — Memory Broker, protection domains and encryption

Status: implementation  
Roadmap: docs/product/mvp-roadmap.md  
Depends on: MVP-20  
Owner PR: #46

## Goal

Make private and family-shared Memory technically separable so Ada can request only
the domain(s) needed for one trusted actor/audience context, while current Markdown
and its recovery history are encrypted at rest and remain directly human-editable
when intentionally unlocked.

## Current state / evidence

- MVP-20 is done on main via PR #41.
- ADR-0008 already selects a host-side Memory Broker and private-by-default,
  independently protected Memory domains.
- ADR-0010 provides safe current-file semantics and Git recovery history, but leaves
  the final shared-working-tree race and trusted repo-local Git metadata to MVP-30.
- FileMemoryStore currently owns one root and GitMemoryHistory assumes
  <root>/.git; no protection-domain broker or encryption exists yet.
- docs/research/memory-protection-evaluation.md evaluates maintained/platform
  protection mechanisms. ADR-0011 records the proposed topology.

## Scope

- opaque protection-domain identities and kinds;
- trusted actor/audience/authorization/operation context with no caller-selected
  domain/path/key;
- fail-closed broker scope binding;
- separate host-side production broker boundary;
- per-domain encrypted current Memory and encrypted Git history;
- broker-only key/root handling;
- independently configurable source/document provider boundary per domain;
- restart, lock/unlock, backup/restore and cross-domain negative tests;
- explicit concurrency decision required by the roadmap.

## Non-goals

- automatic learning/staleness and contradiction resolution (MVP-40);
- derived FTS/vector/graph retrieval (MVP-40);
- family-facing chat integration (MVP-50);
- cloud sync or a public Git remote;
- permanent historical erasure policy;
- cross-platform encrypted-vault implementation in the first macOS slice.

## Open decisions

These remain blockers for ADR-0011 acceptance, not invitations to guess:

1. target-Mac Keychain access-control shape for a broker process;
2. exact platform encrypted-image command/format after the macOS probe;
3. whether ADR-0010's final late non-cooperating-save race is accepted as an MVP
   residual or closed through a separately designed synchronization slice;
4. broker lifecycle/startup ownership for the final packaged product (MVP-90 may own
   packaging, but MVP-30 must prove restart behavior).

## Reuse / dependency evidence

See docs/research/memory-protection-evaluation.md.

Proposed KISS direction for the first macOS MVP:

- adapt the platform encrypted-volume facility behind an Ada-owned provider;
- use Keychain for small per-domain secrets;
- keep the broker/process/domain contract Ada-owned;
- do not add a live-vault dependency merely to abstract a future Linux deployment.

gocryptfs remains a credible later Linux candidate. CryFS is rejected while its
current major version is explicitly experimental/data-loss-prone. Cryptomator is a
larger Java/application dependency with GPL/AGPL or commercial distribution
considerations. age remains a candidate for backup/export rather than a live
human-editable filesystem.

## Security / privacy / authority

- Broker access is storage scoping, not authorization. AdaGuard/trusted application
  context decides what may be requested; the broker enforces only an exact bound
  scope.
- Model output and retrieved content never create actor/audience/authorization
  context and never choose a protection-domain ID.
- The normal runtime must not receive all domain roots/keys.
- A fully compromised Ada runtime that can forge trusted broker context remains the
  explicit ADR-0008 MVP residual threat.
- Domain IDs are opaque and non-semantic.
- Keys/credentials never enter Memory, Git, config, logs, command arguments or
  model context.
- Current Memory and Git history are both encrypted at rest.
- Git is history only and never an auth boundary.
- Tests use synthetic identities/data only.

## Interfaces and data ownership

S1 introduces:

- ProtectionDomainRef: opaque domain identity + kind only;
- MemoryAccessContext: trusted actor/audience/authorization/operation tuple,
  deliberately without a domain/path/key;
- MemoryScope: exact broker-resolved domain set;
- MemoryBrokerPort.resolve_scope(): fail-closed domain resolution.

The S1 InMemoryMemoryBroker is contract/test infrastructure only. It is not a
production security boundary and must never be used with real household Memory.

Later slices keep filesystem paths, mount points, Git directories, keys and source
provider credentials entirely behind the host-side broker/provider adapters.

## Implementation slices

### S1 — Broker/domain contract

- add Ada-owned protection-domain and access-context types;
- add MemoryBrokerPort;
- add a deterministic in-memory contract adapter for tests only;
- prove exact-match/fail-closed scope behavior and absence of caller-selectable
  domain/path/key fields;
- add reuse evidence and proposed ADR-0011.

### S2 — Host process + encrypted-vault provider probe

- implement local-only broker IPC with restrictive permissions;
- define EncryptedVaultProvider behind the adapter boundary;
- target-Mac synthetic probe for encrypted create/unlock/lock/restart;
- validate Keychain item access restrictions and secret handling;
- keep platform command details out of core/ports.

### S3 — Protected current Memory + separated history

- make GitMemoryHistory support a broker-controlled Git directory separate from
  the human-edit working tree;
- route one synthetic domain through FileMemoryStore with encrypted current and
  history surfaces;
- preserve current-only semantic reads and existing MVP-20 correction/forget
  behavior.

### S4 — Multiple private/shared domains

- configure at least two synthetic private domains plus one shared domain;
- prove self/private and family/shared actor/audience scopes differ;
- prove normal/model-driven paths cannot access the unrelated private domain;
- add the provider-config boundary for later source/document access without
  implementing retrieval early.

### S5 — Recovery, backup and concurrency decision

- detach/copy/restore encrypted vaults and verify current + history state after
  restart;
- test interrupted lock/unlock/mount cleanup and fail-closed provider errors;
- resolve the multi-workspace versus accepted-residual decision in ADR-0011;
- update threat/privacy docs and durable TODOs.

## Acceptance / Definition of Done

MVP-30 is complete only when:

- synthetic person-private A cannot read/disclose person-private B through the
  normal/model-driven path;
- shared access is explicit and audience-bound;
- the ordinary runtime has no standing all-vault root/key capability;
- current Memory and Git history are encrypted at rest and survive restart;
- human-readable current Markdown remains directly editable when intentionally
  unlocked;
- Git metadata executed by Ada is not writable from the ordinary editor/sync
  surface;
- missing/ambiguous actor/audience/authorization scope fails closed;
- a detached encrypted backup/restore round-trip succeeds;
- the roadmap-required concurrency model is explicitly decided and tested;
- independent review and exact-head validation are complete.

## Validation

S1:

    python -m unittest tests.test_memory_broker_contract
    python -m unittest tests.test_architecture_boundaries
    sh scripts/validate.sh

Later slices add target-Mac platform probes and restart/restore tests. Validation
evidence is commit-specific and belongs in the PR.

## Review focus

- any caller-controlled field that can widen domain scope;
- accidental path/key leakage across the broker port;
- confused-deputy behavior between actor and audience;
- treating the broker as an authorization engine;
- any normal runtime process that still receives all vault credentials;
- plaintext Git objects/config outside encrypted broker-controlled storage;
- Keychain access broader than the broker needs;
- mount/unlock crash cleanup and stale mounted volumes;
- silent last-writer-wins or an unjustified claim that Git solves human-edit races.

## Follow-ups

Items outside MVP-30 remain in docs/todo.md; MVP-40 owns learning/retrieval and
MVP-90 owns final packaging/service installation. Material residuals discovered
during this step must be copied to docs/todo.md before merge.
