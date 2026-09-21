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

### Confirmed maintainer direction

The authoritative Memory should feel closer to a durable personal knowledge base than to an opaque agent database.

Current direction:

- **Markdown-first** for ordinary memories, relationships, routines, explanations, and notes;
- optional **YAML properties/front matter** for small machine-readable fields such as scope, subject, dates, addresses, lifecycle state, or provenance;
- schema-light rather than ontology-first: useful structure may emerge over time instead of being fixed up front;
- compatible with ordinary editors and tools such as Obsidian, but **not dependent on Obsidian** for correctness or runtime operation;
- periodic "Memory gardening" may reorganize, deduplicate, summarize, or suggest cleanup, but destructive merges/deletions must remain visible and deliberate.

Structured formats such as dedicated YAML/TOML records remain possible where they materially improve a narrow data type, but they should not replace readable Markdown as the default human surface.

### Confirmed scope/layout convention

The maintainer confirmed the following separation:

- **directory location is the hard privacy/audience boundary**;
- **YAML properties/front matter carry metadata inside that boundary**;
- **Markdown is the primary human-readable content**.

Illustrative layout:

```text
memory/
├── shared/
│   ├── family/
│   └── ...
├── people/
│   ├── <person-id>/
│   │   ├── private/
│   │   └── ...
│   └── ...
└── ada/
    └── personality/
```

The exact directory taxonomy remains open and should be scenario-driven, but access control must not depend on free-text tags or model interpretation. Moving a note across a hard-scope directory boundary is therefore a security-relevant operation and must eventually be mediated by deterministic Ada policy rather than silently inferred by the model.

YAML metadata may describe properties such as:

- subject/person;
- type;
- tags;
- dates;
- lifecycle/correction state;
- provenance/source reference;
- optional structured fields such as addresses.

YAML metadata must not be treated as an alternate authorization system. Authority remains owned by AdaGuard.

### Confirmed default placement policy: private by default

Newly learned personal knowledge is stored **private by default**.

A memory may enter a shared scope only when at least one of the following is true:

- the user explicitly states that the information is shared/common household knowledge;
- the source itself has a deterministically established shared audience and the memory semantics are safe to preserve at that same scope;
- a later explicit Ada-owned rule classifies a narrowly defined memory type as shared.

The model must not widen scope merely because information appears useful for coordination.

Examples:

- a person's preference -> private by default;
- a household fact explicitly stated as common information -> may be shared;
- a person's medical appointment -> remains private unless an explicit rule/grant establishes a permitted shared abstraction.

Where coordination requires broader visibility, Ada should prefer a deliberately minimized shared derivative (for example, `busy` or `needs transport`) over copying private details into shared Memory. Such derivatives still require an explicit future policy and must preserve provenance to the private source without exposing the source content.

### Confirmed learning direction: evidence-based and class-dependent

Memory ingestion should not use one universal rule. Different classes of knowledge need different learning paths.

Ada should support a small learning lifecycle:

```text
observation
  -> hypothesis
  -> confirmed / established Memory
  -> later superseded, corrected, or forgotten
```

An **observation is not yet an authoritative fact**. It records that something happened, was stated, or appeared useful. A hypothesis may be formed from one or more observations, but it remains visibly provisional until the applicable learning rule promotes it.

The simplest useful learning loop is:

1. record a privacy-conscious observation with source/reason and scope;
2. use the current hypothesis when appropriate, without treating it as permission or guaranteed truth;
3. observe whether the resulting suggestion/behavior was accepted, corrected, rejected, or contradicted;
4. strengthen, revise, or discard the hypothesis;
5. only persist a stable fact/preference/routine at the maturity level justified by that evidence.

The system should prefer **state-based maturity** over an opaque universal numeric confidence score.

Maturity and confirmation basis are separate dimensions.

Initial maturity states to characterize are:

- `observed`;
- `provisional`;
- `confirmed`;
- `stale`;
- `contradicted`;
- `superseded`;
- `forgotten`.

`stale` is primarily for learned/observed patterns whose supporting evidence has become too old or too sparse to treat as current. It does not delete the memory and does not imply that the earlier observation was wrong.

For a confirmed memory, Ada should also preserve **how it became confirmed**. Initial confirmation bases are:

- `observed_pattern` — promoted after repeated, sufficiently consistent observed outcomes without an explicit user confirmation;
- `explicit_user` — explicitly confirmed/stated by the relevant user.

This avoids conflating maturity with provenance. For example:

```yaml
state: confirmed
confirmation_basis: observed_pattern
```

and:

```yaml
state: confirmed
confirmation_basis: explicit_user
```

A memory confirmed through observation remains weaker evidence than an explicit confirmation for later contradiction resolution or sensitive decisions. Exact precedence rules still need characterization.

#### Aging and staleness

Ada may automatically move a **pattern-based** memory from `confirmed` to `stale` when its supporting observations have not been refreshed for a sufficiently long time.

This is allowed only when:

- the confirmation basis is observational (for example `observed_pattern`);
- the transition is non-destructive and inspectable;
- the original observations/provenance remain available according to retention policy;
- the rule for staleness is deterministic and category-specific rather than an LLM guess.

Explicitly confirmed durable facts must not become stale merely because time passed. A future memory type may still define an explicit validity window where time is semantically relevant.

Useful metadata to characterize includes:

- `last_observed`;
- `observation_count`;
- optional `valid_from` / `valid_until`;
- optional category-specific staleness policy.

A stale pattern may later be:

- reconfirmed by new consistent observations;
- explicitly confirmed by the user;
- superseded by a newer pattern;
- contradicted and left unresolved until clarified.

#### Contradiction and explicit correction

Ada must distinguish between a **new contradictory statement** and an **explicit correction**.

A new contradictory statement does not automatically supersede existing confirmed Memory merely because it is newer.

Example:

```text
earlier: "Music lesson is Wednesday."
later:   "Music lesson is Thursday."
```

Absent explicit correction semantics or another deterministic resolution rule, Ada should preserve both claims as a visible contradiction and mark the affected memory as `contradicted`.

By contrast, explicit correction language such as:

```text
"No, not Wednesday — Thursday."
```

may deterministically supersede the corrected claim:

```text
Wednesday -> superseded
Thursday  -> confirmed / explicit_user
```

Initial evidence precedence for conflict handling is:

```text
explicit_user > observed_pattern > provisional > observed
```

This precedence is **not** a blanket last-write-wins rule.

Rules:

- two plausible explicit-user claims that conflict remain unresolved unless one clearly corrects the other;
- an explicit correction may supersede an observational pattern;
- an observational pattern must not overwrite an explicit-user claim merely through repetition;
- contradictions remain inspectable and should be surfaced when relevant;
- resolution should preserve provenance for both the superseded and surviving claims;
- model inference alone must not decide that one ambiguous explicit claim "probably" wins.

Exact field names remain open, but both maturity and confirmation basis must remain visible in human-readable Memory.

#### Confirmed initial learning classes

The maintainer confirmed four default learning classes. More specific classes may be added later, but they must map back to one of these behaviors rather than silently inventing a new trust level.

| Class | Default behavior | Examples / notes |
| --- | --- | --- |
| **A — explicit, low-risk facts/preferences** | **Remember automatically, private by default**, with provenance and correction/supersession semantics. | "I prefer concise answers." A later explicit correction wins. |
| **B — inferred preferences/routines** | **Observe first, learn gradually.** Record minimized observations, form a provisional hypothesis, and promote after repeated evidence as `confirmed/observed_pattern` or after explicit confirmation as `confirmed/explicit_user`. | Repeatedly choosing one option; recurring pickup patterns. Never implies authority. |
| **C — sensitive or consequential facts** | **Require confirmation or an explicit future rule before durable promotion.** | Health, finances, highly personal information, facts whose incorrect persistence could materially affect people. |
| **D — secrets/credentials** | **Never learn automatically.** | Passwords, API tokens, authentication secrets, private keys, recovery codes. Explicit requested secure storage is a separate future capability, not ordinary Memory learning. |

Cross-cutting rules still apply:

- shared facts remain subject to the confirmed shared-scope rules; class A does not mean "share automatically";
- untrusted/quoted content is source evidence only and cannot directly become class-A trusted Memory;
- an observation may be retained in the learning journal without promoting it to authoritative Memory;
- classification itself must be explainable and correctable; material ambiguity should choose the more conservative class.

#### Feedback signals

Learning may use multiple feedback forms with different evidentiary weight:

- explicit correction or rejection — strong negative evidence;
- explicit confirmation — strong positive evidence and `explicit_user` confirmation basis;
- user selecting/accepting a suggestion — useful but weaker positive evidence;
- a real-world outcome explicitly reported back to Ada — useful outcome evidence;
- repeated consistent behavior across occasions — cumulative evidence that may eventually justify `observed_pattern` confirmation;
- silence / absence of correction — **not sufficient on its own** to establish a durable fact.

When Ada acts or proposes based on a provisional hypothesis, the relevant outcome may be referenced from existing action/application records, but the durable action ledger must not become a hidden personal Memory store. Memory should retain only the minimized learning fact/provenance needed for future behavior.

#### Learning journal / observation record

Ada may maintain an inspectable, privacy-scoped learning journal for observations that are not yet mature enough to become ordinary Memory notes.

Requirements:

- it belongs to the same human-controlled Memory domain, not a hidden runtime database;
- it follows the same hard directory privacy boundaries;
- it stores minimized observations rather than raw conversations by default;
- entries may expire or be compacted once promoted, rejected, superseded, or no longer useful;
- rebuilding retrieval indexes must not change learning maturity;
- users can inspect/correct/remove learning observations.

The exact representation remains open; Markdown/YAML or another human-readable append-friendly form should be characterized.

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

### 1. Authoritative human-controlled Memory

This is the user/operator-controlled source of truth. The default representation should be a directory/vault of Markdown notes that remains understandable without Ada.

Required properties:

- human-readable, with Markdown as the default representation;
- directly editable with ordinary tools, including plain text editors and optionally Obsidian;
- may use constrained YAML properties/front matter for small structured fields without turning the note body into a rigid schema;
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
- explicit link graphs derived from Markdown links;
- semantic or inferred knowledge graphs;
- derived search metadata.

Rules:

- it is reconstructible from authoritative Memory;
- it is never an independent truth source;
- deleting/rebuilding it must not lose authoritative Memory;
- stale index state must be detectable and repairable;
- it must preserve enough scope metadata that retrieval cannot widen audience/access boundaries;
- remote embedding/index services are not part of the default local path;
- inferred graph edges remain derived evidence and never become authoritative Memory merely because an indexer generated them.

This split allows Ada to reuse mature retrieval technology without giving an opaque agent-memory database ownership of user truth.

## Hard gates before scoring

A candidate cannot win by weighted score if it fails a hard gate.

| Gate | Requirement |
| --- | --- |
| Human control | Authoritative Memory is human-readable and directly editable without Ada. |
| Open format | The authoritative representation remains usable without a proprietary editor or database runtime. |
| No hidden persistence | No second independent persistent truth store; indexes/caches are reconstructible. |
| Local/offline baseline | Core Memory read/write/retrieval can operate without cloud access. |
| Scope isolation | Individual/private/shared scopes can be represented and enforced without trusting the model. |
| Authority separation | Learned Memory cannot create or widen permissions. |
| Correction semantics | Corrections, supersession, contradiction, and deliberate forgetting can be represented safely. |
| Learning explainability | Observations, hypotheses, promotion, correction, and rejection remain inspectable; no hidden behavioral model silently becomes Memory truth. |
| Deletion/export | Users can inspect, export, edit, and delete authoritative memories; derived state can be rebuilt. |
| Provenance | Material facts can retain useful source/reason attribution without requiring raw source retention. |
| License | Runtime/build dependencies must be compatible with Ada's MIT distribution strategy and documented in NOTICE. |
| Maintenance | Fits the accepted Python/container architecture and the project's roughly 1–2 evenings/week maintenance budget. |

## Candidate architectures

No candidate is selected by this draft.

### A. Ada-owned file-native Memory + derived SQLite index — control option

Concept:

- authoritative Markdown notes in a user-controlled Memory directory/vault;
- optional YAML properties/front matter for compact structured fields such as scope, subject, provenance, lifecycle state, dates, or addresses;
- dedicated YAML/TOML records only where a narrow data type genuinely benefits from them;
- no mandatory fixed ontology beyond the minimum metadata required for safety and scope isolation;
- standard SQLite/FTS5 as one possible derived local search index;
- optional explicit-link, knowledge-graph, or vector retrieval layers added only when characterization proves they materially improve recall/context efficiency;
- embeddings, if used, generated through the already accepted local model boundary or a separately reviewed local embedder.

Potential strengths:

- directly satisfies the human-readable/editable source-of-truth requirement;
- naturally compatible with Obsidian-style personal knowledge workflows without making Obsidian a dependency;
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

### D. Graphify — derived knowledge-graph candidate

Repository: https://github.com/Graphify-Labs/graphify

Relevant fit:

- Apache-2.0;
- builds a queryable graph from code/docs/media rather than a vector index;
- records whether edges are `EXTRACTED` from source or `INFERRED`;
- produces a persistent `graph.json` that can be queried without rereading all source files;
- local-first for deterministic code parsing; documentation/media semantic passes may use a configured model/backend.

Potential Ada role:

- derive relationships and scoped subgraphs from the Markdown Memory vault;
- reduce the amount of raw Memory that must be placed into model context;
- complement lexical/vector retrieval rather than replace authoritative Memory.

Important boundary:

- Graphify output is a **derived index**, especially for `INFERRED` edges;
- inferred relationships must not silently rewrite Markdown Memory or become permission/action truth;
- any semantic pass over personal Memory must use Ada's approved local/egress boundary.

Current status: **promising derived knowledge-graph candidate; not an authoritative Memory store**.

### E. Graphiti

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

### F. Letta memory / MemFS

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

### G. Dedicated vector database as authoritative Memory

Examples include Qdrant, Chroma, or similar stores.

This architecture is retained only as a control comparison.

Initial concern:

- vector/database records are not the human-readable directly editable source of truth required by Ada;
- they may still be useful as a derived retrieval layer.

Current status: **likely hard-gate failure as authoritative Memory; potentially valid derived index**.

## Retrieval technology questions

The first MVP should not assume semantic vectors are required.

Characterize progressively:

1. deterministic structured lookup for known memory types and YAML properties;
2. Markdown links/backlinks and SQLite FTS5 keyword/full-text retrieval;
3. derived knowledge-graph retrieval such as Graphify for relationship/path/subgraph queries;
4. vector or hybrid lexical + vector retrieval only if it materially improves representative scenario recall or reduces context cost.

Obsidian's own graph is useful as a human visualization of explicit note links. Ada should not assume that this is equivalent to semantic graph extraction: richer inferred relationships belong in a separate derived layer.

Potential optional vector components must be reviewed independently for:

- license;
- Python 3.14 / arm64 / Linux support;
- binary artifact provenance;
- maintenance and release maturity;
- deletion/rebuild correctness;
- local embedding model cost on the M1/16 GB target.

## Memory gardening

A schema-light Markdown Memory will accumulate duplicates, stale notes, fragmented facts, and inconsistent structure over time. That is expected.

Ada should support occasional gardening passes that can:

- detect duplicate or near-duplicate notes;
- surface contradictions and stale facts;
- suggest clearer links, titles, tags, or properties;
- propose merging fragmented notes;
- identify orphaned or low-value derived structure;
- rebuild indexes after outside edits.

Gardening must not silently perform destructive cleanup. Proposed merges, deletions, or material semantic rewrites should remain inspectable and reversible/confirmable according to the eventual Memory authority policy.

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
11. **Gardening** — after Memory accumulates duplicates and stale structure, Ada proposes a cleanup without silently deleting or changing material facts.
12. **Preference learning** — repeated accepted concise replies create a provisional preference hypothesis; repeated consistent outcomes may promote it to `confirmed/observed_pattern`, while an explicit confirmation yields `confirmed/explicit_user`; silence alone never confirms it.
13. **Routine learning** — repeated reported outcomes may establish a routine, but the routine never becomes permission to act.
14. **Learning correction** — a user rejects a learned hypothesis and Ada stops using it without routine archive rescanning recreating it.
15. **Pattern aging** — an observationally confirmed routine that has not been observed for a category-appropriate period becomes `stale` without being deleted; an explicitly confirmed durable fact does not age merely because time passed.
16. **Contradictory explicit statements** — two conflicting explicit-user claims remain visibly `contradicted` unless one is clearly expressed as a correction or another deterministic resolution rule applies.
17. **Explicit correction** — "not Wednesday, Thursday" supersedes the corrected claim directly while preserving provenance for both versions.

## Evaluation criteria to weight with the maintainer

After hard gates, candidate scoring should consider:

- human editability / explainability;
- retrieval quality and context/token efficiency;
- correction and contradiction semantics;
- learning quality, explainability, and false-learning resistance;
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

1. Define the smallest Ada-owned general Memory semantic model from the scenarios above without turning the vault into a rigid ontology.
2. Characterize **Markdown + constrained YAML properties/front matter** as the canonical default representation; use separate structured files only where justified by a concrete data type.
3. Characterize structured/property lookup + Markdown links + FTS5 before adding more expensive retrieval infrastructure.
4. Compare Graphify-style graph retrieval with vector/hybrid retrieval on representative family-memory questions, including context/token reduction.
5. Verify candidate license/dependency chains from source, not search summaries.
6. Evaluate whether Mem0 contributes enough reusable extraction/update logic without becoming the authoritative store.
7. Determine whether temporal graph behavior from Graphiti solves an MVP problem that simpler correction/supersession records plus a derived graph do not.
8. Decide how concurrent/out-of-band file edits are detected and reconciled.
9. Define explicit forget/delete semantics across authoritative files, derived indexes/graphs, source references, and action/audit records.
10. Define the Memory-gardening proposal/approval boundary.
11. Characterize learning promotion rules for explicit facts, preferences, routines, sensitive facts, and shared knowledge, including precedence between observed-pattern and explicit-user confirmation.
12. Define the inspectable learning-journal representation, retention/compaction rules, and how application outcomes feed learning without duplicating the action ledger.
13. Define deterministic, category-specific staleness rules for observed patterns and which memory types, if any, have explicit validity windows.
14. Characterize explicit correction detection and contradiction-resolution rules without relying on model-only last-write-wins behavior.
15. Keep Memory-derived values distinct from explicit/context-derived values until this ADR defines trustworthy provenance; ADR-0007 intentionally deferred `memory_derived`.

## Decision status

No Memory backend is adopted by this draft.

The next step is evidence-driven characterization of the file-native control path and the strongest reuse candidates, followed by an agreed weighted matrix and independent review before this ADR can move to Accepted.
