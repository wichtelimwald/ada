# ADR-0009 — Memory history adapter

Status: Accepted
Date: 2026-09-26
Decision scope: MVP-20 file-native Memory versioning
Supersedes: none
Extends: ADR-0008

## Context

ADR-0008 accepts human-editable Markdown as authoritative Memory and identifies
Git-style per-protection-domain history as the leading MVP versioning adapter.
MVP-20 must now capture out-of-band edits, preserve reversible Ada writes, and
keep history strictly separate from current semantic Memory.

The runtime image is based on `python:3.14-slim` and does not install the Git
CLI. Adding history therefore needs either a runtime Git implementation, a
system Git package, or a new custom history format.

Hard requirements:

- current Markdown remains authoritative;
- normal Memory retrieval never rehydrates from history;
- history must be local/offline and scoped to one Memory root/domain;
- no arbitrary working-tree checkout is required;
- direct human edits must be capturable as revisions;
- Ada writes must be attributable without absorbing unrelated concurrent edits;
- Python 3.14 and macOS/Linux must be supported;
- dependency/license/security surface must remain small and reviewable.

## Decision

Use **Dulwich 1.2.15** behind Ada's `MemoryHistoryPort` as the MVP Git-style
history implementation.

Ada uses a **bare history repository** under the configured Memory root. The
adapter receives explicit snapshots of only `memory/*.md` and
`learning/*.md`, creates Git trees/commits directly, and never checks history
out into the authoritative Memory directories. This deliberately avoids a
shared Git index/working-tree staging model.

The file store captures current direct edits before consuming or changing them.
For Ada writes it records the intended snapshot separately, then compares the
actual current snapshot. A concurrent external edit is captured as a later
revision and reported as a conflict rather than silently treated as Ada's
result.

Git history is operational recovery/versioning state. It is not an
authorization source, authentication evidence, retrieval source, learning
source, or current Memory source.

## Why Dulwich

Dulwich is a standalone Git implementation for Python and does not require the
Git executable or native libgit2 for its normal Python API. Release 1.2.15
supports Python 3.14 and publishes a pure-Python wheel.

License:

- Dulwich 1.2.15: `Apache-2.0 OR GPL-2.0-or-later`; Ada uses it under the
  Apache-2.0 option.
- Required runtime dependency `urllib3>=2.2.2`: MIT.

Security review:

- Dulwich published multiple checkout/path hardening fixes during 2026,
  including GHSA-8w8g-wq8h-fq33 fixed in 1.2.8 and further path hardening
  through 1.2.12.
- Ada pins 1.2.15, newer than those fixes.
- Ada's adapter does not use clone, checkout, merge, archive extraction,
  submodules, network transport, or shell merge drivers. It writes Git objects
  and refs for Ada-supplied in-memory snapshots only, reducing exposure to those
  attack surfaces.

Primary sources:

- https://pypi.org/project/dulwich/1.2.15/
- https://github.com/jelmer/dulwich
- https://github.com/jelmer/dulwich/security/advisories/GHSA-8w8g-wq8h-fq33
- https://github.com/jelmer/dulwich/releases

## Alternatives considered

### System Git subprocess

Strengths:

- mature implementation;
- already characterized by Ada's research control;
- excellent inspection/recovery tooling.

Rejected for the MVP runtime because Ada would need to add and maintain a
system executable/package in the slim container and harden subprocess
environment/config behavior. The accepted runtime currently has no Git CLI.

Re-open if native Git becomes an existing mandatory runtime dependency or
Dulwich proves unreliable for Ada's narrow local object/ref operations.

### pygit2 / libgit2

Strengths:

- mature Git semantics;
- strong low-level API.

Rejected because it introduces native libgit2 packaging and platform
distribution complexity for a small local history use case.

Re-open if Ada later needs Git operations where libgit2 materially improves
correctness or performance.

### Custom snapshot/version store

Could be very small initially, but it would make Ada own a new version-control
format, recovery tooling, retention semantics and corruption behavior despite
Git already matching the accepted architecture.

Rejected under reuse-first/KISS.

## Consequences

Positive:

- no Git executable is required in the runtime image;
- history remains compatible with standard Git object semantics;
- the authoritative Markdown format is not coupled to Dulwich;
- a bare repository avoids shared-index staging contamination;
- no checkout path can rewrite authoritative Memory.

Costs / risks:

- Dulwich and urllib3 become runtime dependencies and must stay in dependency
  and release-artifact review.
- Historical revisions may retain sensitive content after operational
  forgetting. ADR-0008 intentionally treats historical purge/backup retention
  as a separate concern.
- Git commit identity does not authenticate a human editor.
- Arbitrary editors do not honor Ada's advisory lock. MVP-20 therefore combines
  Ada-process locking, optimistic revision tokens, a pre-publication revision
  recheck, and post-write snapshot reconciliation. Protection-domain access
  control remains MVP-30.

## Re-open triggers

Revisit this decision if any of the following becomes true:

- a Dulwich security/advisory issue affects the object/tree/ref operations Ada
  uses and no timely safe version is available;
- exact target macOS/Linux validation shows corruption, durability or
  interoperability failures;
- the runtime already requires system Git for another accepted capability;
- recovery requirements demand Git operations that materially exceed Dulwich's
  narrow use here;
- dependency/distribution review finds an unacceptable transitive or licensing
  consequence.
