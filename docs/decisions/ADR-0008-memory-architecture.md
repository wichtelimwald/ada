# ADR-0008: Authoritative Memory and retrieval architecture

- **Status:** Proposed
- **Date:** 2026-09-21

## Context

Ada's first MVP requires persistent personal and household memory, but the Memory architecture is intentionally still open.

The confirmed product baseline requires Memory to be:

- external to Ada runtime persistence;
- human-readable and directly editable without Ada;
- respected when edited outside Ada;
- available for local/offline chat;
- correctable, inspectable, exportable, and deliberately forgettable;
- scoped so private and shared household context do not collapse into one global profile;
- attributable enough to explain important remembered facts and corrections;
- separate from permission, authentication, action truth, and the durable action ledger.

Existing architecture already introduced a deliberately narrow `PersonalityMemoryPort` so local chat can define a personality bootstrap lifecycle without preselecting the general Memory backend.

The intended personality lifecycle is:

```text
empty authoritative Memory
  -> seed distribution personality exactly once
  -> existing Memory wins on later starts/upgrades
  -> personality may evolve through inspectable, attributable changes
```

This ADR evaluates the general authoritative Memory and retrieval architecture. It does not allow Memory to create authority.

## Security and semantic invariants

The following remain non-negotiable:

```text
Person != Data Subject != Audience != Authority
Learned != Authorized
Memory != Permission
Memory != Action Truth
Authoritative Memory != Derived Index
```

In particular:

- familiar behavior, repeated past actions, learned routines, model output, retrieved text, and remembered preferences cannot grant permission;
- untrusted email, forwarded content, files, websites, tool output, or model output cannot directly rewrite trusted Memory;
- corrections supersede outdated knowledge rather than silently coexisting as equally current truth;
- contradiction must remain visible until resolved;
- source deletion does not automatically delete a derived memory, but deliberate memory deletion/forgetting must remove that memory and any reconstructible index entries derived from it;
- credentials must not be learned automatically;
- the action ledger remains a separate operational record and is not a substitute for personal Memory.

## Architectural split

Ada should evaluate Memory as two distinct layers.

### 1. Authoritative Memory

This is the user/operator-controlled source of truth.

Required properties:

- human-readable;
- directly editable with ordinary tools;
- stable on disk independently of Ada process state;
- supports private/shared scopes;
- supports provenance/reason/source references where materially useful;
- supports correction/supersession and contradiction state;
- supports deletion/export;
- preserves existing Memory across Ada upgrades;
- allows deterministic validation before content becomes trusted Memory.

### 2. Derived retrieval/index layer

This layer exists only to make authoritative Memory efficiently retrievable.

It may contain:

- full-text indexes;
- embeddings;
- semantic chunks;
- normalized lookup keys;
- derived search metadata.

Rules:

- it is reconstructible from authoritative Memory;
- it is never an independent truth source;
- deleting/rebuilding it must not lose authoritative Memory;
- stale index state must be detectable and repairable;
- it must preserve enough scope metadata that retrieval cannot widen audience/access boundaries;
- remote embedding/index services are not part of the default local path.

This split allows Ada to reuse mature retrieval technology without giving an opaque agent-memory database ownership of user truth.

## Hard gates before scoring

A candidate cannot win by weighted score if it fails a hard gate.

| Gate | Requirement |
| --- | --- |
| Human control | Authoritative Memory is human-readable and directly editable without Ada. |
| No hidden persistence | No second independent persistent truth store; indexes/caches are reconstructible. |
| Local/offline baseline | Core Memory read/write/retrieval can operate without cloud access. |
| Scope isolation | Individual/private/shared scopes can be represented and enforced without trusting the model. |
| Authority separation | Learned Memory cannot create or widen permissions. |
| Correction semantics | Corrections, supersession, contradiction, and deliberate forgetting can be represented safely. |
| Deletion/export | Users can inspect, export, edit, and delete authoritative memories; derived state can be rebuilt. |
| Provenance | Material facts can retain useful source/reason attribution without requiring raw source retention. |
| License | Runtime/build dependencies must be compatible with Ada's MIT distribution strategy and documented in NOTICE. |
| Maintenance | Fits the accepted Python/container architecture and the project's roughly 1–2 evenings/week maintenance budget. |

## Candidate architectures

No candidate is selected by this draft.

### A. Ada-owned file-native Memory + derived SQLite index — control option

Concept:

- authoritative Markdown/TOML/YAML files in a user-controlled Memory directory;
- Ada-owned minimal schema for identity/scope, subject, provenance, lifecycle, and correction state;
- standard SQLite/FTS5 as a derived local search index;
- optional vector retrieval added only if characterization proves it materially improves recall;
- embeddings, if used, generated through the already accepted local model boundary or a separately reviewed local embedder.

Potential strengths:

- directly satisfies the human-readable/editable source-of-truth requirement;
- simple deletion/export/backup semantics;
- no mandatory service;
- aligns with the accepted modular Python monolith;
- derived index can be destroyed and rebuilt;
- Ada owns the semantic model without owning a complex database engine.

Risks / work:

- Ada must define the Memory file schema and migration/versioning rules;
- correction, contradiction, concurrent edit, and index reconciliation semantics are Ada-owned work;
- semantic retrieval quality must be characterized rather than assumed.

This is the control option. It is not preferred merely because it is custom.

### B. sqlite-memory

Repository: https://github.com/sqliteai/sqlite-memory

Relevant fit:

- explicitly describes Markdown files as the source of truth;
- supports local SQLite-based hybrid retrieval;
- supports directory synchronization and deletion cleanup;
- offers local embeddings through llama.cpp.

Important gate issue:

- the current repository license is **Elastic License 2.0 with an additional open-source-project grant**, not MIT;
- this is not treated as a permissive-license PASS for Ada without explicit review;
- optional/local dependency and artifact provenance must also be reviewed.

Operationally, it also introduces compiled SQLite extensions and llama.cpp integration that may be more machinery than Ada needs initially.

Current status: **CONDITIONAL pending license and dependency-path review**.

### C. Mem0 OSS

Repository: https://github.com/mem0ai/mem0

Relevant fit:

- Apache-2.0 project;
- supports local/self-hosted operation;
- documented fully local configuration can use Ollama for both LLM and embeddings;
- provides memory extraction/update/search/history concepts and user metadata/filtering.

Mismatch to investigate:

- its normal authoritative state is database/vector-store based rather than a human-editable file source of truth;
- defaults use OpenAI unless deliberately overridden;
- adopting Mem0 as the authoritative store could violate Ada's external human-readable Memory requirement.

Possible role: evaluate whether reusable extraction/conflict/retrieval logic can sit behind an Ada boundary while Ada files remain authoritative.

Current status: **candidate for adaptation/derived capability, not yet demonstrated as authoritative Memory**.

### D. Graphiti

Repository: https://github.com/getzep/graphiti

Relevant fit:

- Apache-2.0;
- temporal knowledge graph and hybrid retrieval are strong matches for evolving facts and relationships;
- supports local/on-prem graph databases and can be configured for local model endpoints.

Mismatch / cost:

- requires a graph-store runtime such as FalkorDB or Neo4j for the normal path;
- authoritative data is not directly human-editable source files;
- current package includes telemetry that must be explicitly disabled for Ada;
- ingestion relies heavily on LLM extraction and structured output;
- operational complexity appears high relative to the MVP and maintenance budget.

Current status: **specialist reference / possible derived graph layer, not yet demonstrated as authoritative Memory**.

### E. Letta memory / MemFS

Repository: https://github.com/letta-ai/letta-code

Relevant fit:

- Apache-2.0;
- mature work on stateful agents, memory blocks, external memory, and local memory filesystem projection;
- filesystem-oriented memory evolution is useful reference material.

Mismatch:

- memory is tightly coupled to Letta's stateful-agent/runtime model;
- Ada has already selected PydanticAI behind an Ada-owned runtime boundary;
- replacing that ownership model merely to gain Memory would create unnecessary architecture coupling;
- git-style history can conflict with strong deletion/forgetting semantics if used as the authoritative retention mechanism.

Current status: **reference / component-reuse investigation, not a default runtime replacement**.

### F. Dedicated vector database as authoritative Memory

Examples include Qdrant, Chroma, or similar stores.

This architecture is retained only as a control comparison.

Initial concern:

- vector/database records are not the human-readable directly editable source of truth required by Ada;
- they may still be useful as a derived retrieval layer.

Current status: **likely hard-gate failure as authoritative Memory; potentially valid derived index**.

## Retrieval technology questions

The first MVP should not assume semantic vectors are required.

Characterize progressively:

1. deterministic structured lookup for known memory types;
2. SQLite FTS5 keyword/full-text retrieval;
3. hybrid lexical + vector retrieval only if it materially improves representative scenario recall.

Potential optional vector components must be reviewed independently for:

- license;
- Python 3.14 / arm64 / Linux support;
- binary artifact provenance;
- maintenance and release maturity;
- deletion/rebuild correctness;
- local embedding model cost on the M1/16 GB target.

## Required representative Memory scenarios

Before selecting a backend, characterize at least:

1. **Personality bootstrap** — empty Memory seeds once; existing edited personality wins.
2. **Outside edit** — user edits a Memory file while Ada is stopped; next start respects it and rebuilds stale derived state.
3. **Correction** — “music lesson is now Wednesday, not Tuesday” supersedes the earlier fact and future retrieval prefers the correction.
4. **Contradiction** — two credible unresolved pickup times remain visibly conflicting rather than one silently winning.
5. **Private/shared scope** — one adult's private fact must not appear in a family briefing, while permitted busy-time abstraction may still be used where separately allowed.
6. **Provenance after source deletion** — derived Memory can retain coarse attribution without keeping the deleted original recoverable.
7. **Forget** — deleting a memory removes it from subsequent retrieval and rebuilt indexes.
8. **No authority from learning** — a remembered preference or repeated past action cannot satisfy AdaGuard.
9. **No archive rescan** — deleted/forgotten information is not silently relearned from archived messages unless an explicit archive-read task permits it.
10. **Offline recall** — representative local chat retrieval works with network access unavailable.

## Evaluation criteria to weight with the maintainer

After hard gates, candidate scoring should consider:

- human editability / explainability;
- retrieval quality;
- correction and contradiction semantics;
- privacy/scope isolation;
- local/offline behavior;
- operational simplicity;
- integration effort with current Python/PydanticAI architecture;
- resource use on M1/16 GB;
- portability to later Linux/vServer deployment;
- dependency/security maturity;
- replaceability and data portability;
- ongoing maintenance effort.

Weights are deliberately not assigned by this draft.

## Open research before a decision

1. Define the smallest Ada-owned general Memory semantic model from the scenarios above.
2. Decide the canonical file representation to characterize first (for example Markdown + constrained front matter versus TOML/YAML records).
3. Characterize plain structured lookup + FTS5 before adding vector infrastructure.
4. Verify candidate license/dependency chains from source, not search summaries.
5. Evaluate whether Mem0 contributes enough reusable extraction/update logic without becoming the authoritative store.
6. Determine whether temporal graph behavior from Graphiti solves an MVP problem that simpler correction/supersession records do not.
7. Decide how concurrent/out-of-band file edits are detected and reconciled.
8. Define explicit forget/delete semantics across authoritative files, derived indexes, source references, and action/audit records.
9. Keep Memory-derived values distinct from explicit/context-derived values until this ADR defines trustworthy provenance; ADR-0007 intentionally deferred `memory_derived`.

## Decision status

No Memory backend is adopted by this draft.

The next step is evidence-driven characterization of the file-native control path and the strongest reuse candidates, followed by an agreed weighted matrix and independent review before this ADR can move to Accepted.
