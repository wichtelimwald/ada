# ADR-0008: Authoritative Memory and retrieval architecture

- **Status:** Accepted
- **Date:** 2026-09-21
- **Accepted:** 2026-09-25

## Context

Ada's first MVP requires persistent personal and household memory. This ADR records the accepted architecture boundary; implementation details and optional derived components remain separately gated.

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
- optional **YAML properties/front matter** only where a machine-readable field adds value without duplicating or silently diverging from a human-edited claim;
- schema-light rather than ontology-first: useful structure may emerge over time instead of being fixed up front;
- compatible with ordinary editors and tools such as Obsidian, but **not dependent on Obsidian** for correctness or runtime operation;
- periodic "Memory gardening" may reorganize, deduplicate, summarize, or suggest cleanup, but destructive merges/deletions must remain visible and deliberate.

Structured formats such as dedicated YAML/TOML records remain possible where they materially improve a narrow data type, but they should not replace readable Markdown as the default human surface.

### Confirmed scope/layout convention

The maintainer confirmed the following separation:

- **directory/vault placement expresses the privacy/audience boundary**;
- **the storage protection boundary must enforce that placement** through separate storage roots, OS access control, encryption keys, or another deterministic mechanism;
- **optional YAML properties/front matter may carry distinct file-level metadata inside that boundary**; claim-level metadata must not become a separate, drifting copy of human-edited text;
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

The exact directory/vault taxonomy remains open and should be scenario-driven, but access control must not depend on free-text tags or model interpretation.

A directory name **alone is not a security boundary** if the same filesystem principal can read all directories. The logical scope boundary therefore needs a corresponding enforceable storage boundary.

Moving a note across a scope/storage boundary is a security-relevant operation and must eventually be mediated by deterministic Ada policy rather than silently inferred by the model.

Optional YAML may carry distinct file-level properties such as a stable note
identifier, title, tags, or creation date. Claim-specific provenance and
lifecycle information must remain human-inspectable with the claim they
describe; the same fact must not be maintained in both prose and YAML.
Structured data such as an address may live in YAML only where YAML is its
single canonical representation rather than a duplicate of the note body.

YAML metadata must not be treated as an alternate authorization system. Authority remains owned by AdaGuard.

### Confirmed storage and access topology

The accepted topology uses **multiple human-readable Memory vaults rather than one monolithic plaintext vault**, with a **host-side Memory Broker** mediating Ada's runtime access to those protection domains:

```text
memory/
├── shared-household/       # shared protection domain
├── person-a-private/       # private protection domain / key / ACL
├── person-b-private/       # private protection domain / key / ACL
├── ...
└── ada-system/             # Ada-owned non-user/private configuration such as personality seed state
```

The names and exact ownership model remain open. The important property is that gaining read access to one private Memory domain must not automatically reveal another person's private Memory.

The **host-side Memory Broker** owns or mediates access to the underlying
vaults and any protection-domain-specific derived retrieval state. The Ada
runtime requests only the protection domain(s) required for the current
authenticated/authorized task; the broker must not expose all household
vaults to one long-lived Ada runtime principal. The broker is an Ada-owned
security boundary, not a model tool and not an authorization engine:
AdaGuard/actor-audience context determines what may be requested, while the
broker enforces the resulting scoped storage access.

Still to decide at implementation level:

- exact vault/repository granularity per person/shared audience;
- OS permissions versus per-vault encryption/keys versus both;
- broker IPC/API and how request identity/scope is bound so caller-controlled
  parameters cannot widen access;
- how derived indexes/graphs are partitioned so they cannot recombine private scopes into one readable database;
- whether indexes are one-per-vault, encrypted per scope, or held only ephemerally;
- how authorized household members edit their own vaults without routing ordinary human editing through Ada;
- how shared minimized derivatives reference a private source without exposing that source.

This also means a single global Obsidian vault is only acceptable where all users of that vault are authorized to read all contained material. Separate private vaults may still each be opened independently in Obsidian.

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

Memory ingestion should not use one universal rule. Different classes of knowledge need different learning paths. **This learning distinction is part of the accepted architecture from the first implementation slice**, even if autonomous promotion/aging rules are implemented incrementally. The initial representation must not collapse explicit user statements, observations, hypotheses, and established Memory into one indistinguishable fact type.

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

This avoids conflating maturity with provenance. In a future inspectable learning-journal entry, a confirmed observation would
have an `observed_pattern` basis while a directly confirmed statement would
have an `explicit_user` basis. This is a semantic distinction, **not** a
requirement for a second structured truth store alongside human-edited
Markdown. Any user-visible Memory state must have one authoritative,
inspectable representation; the research fixture's parallel YAML and prose
are not the MVP schema.

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

#### Confirmed knowledge/evidence roles and promotion boundary

Ada must not encode "what the knowledge is", "how Ada learned it", and
"how mature/trusted it is" as one overloaded field. These are separate axes.

**Durable Memory kind** describes the content that Ada may eventually use as
established Memory, for example:

- `preference` — an explicit or deliberately promoted user preference;
- `fact` — a relatively objective durable fact;
- `routine` — an established recurring pattern;
- `episode` — a compact summary of a materially useful interaction/event.

This set may grow scenario-by-scenario; it is not a fixed ontology.

**Evidence origin** describes how the candidate knowledge arose:

- `explicit_statement` — directly stated/confirmed by an authorized user or
  carried by an explicitly trusted structured source;
- `observed_fact` — a comparatively low-interpretation fact extracted from
  an event/document/system observation, such as an appointment time or a
  practice address;
- `behavioral_observation` — observed interaction/behavior that requires more
  interpretation, such as repeatedly asking for more detail or reacting
  positively to nerdy humor;
- `hypothesis` — an interpretation synthesized from one or more observations.

**Lifecycle/maturity** remains a separate axis
(`observed`, `provisional`, `confirmed`, `stale`, `contradicted`,
`superseded`, `forgotten`).

This means, for example, a `preference` may originate from an
`explicit_statement` or may be promoted from repeated
`behavioral_observation`; an `observed_fact` may later become an
established `fact` after validation. These paths do not have the same
evidentiary weight merely because they end in the same Memory kind.

**Promotion/assimilation is an explicit architecture boundary:**

```text
source/event/outcome
  -> evidence (explicit statement | observed fact | behavioral observation)
  -> optional hypothesis
  -> Ada-owned validation
       - source/trust classification
       - privacy scope
       - learning class / sensitivity
       - provenance/lifecycle
       - contradiction/correction checks
  -> established authoritative Memory, or remain evidence/provisional
```

A model may propose a hypothesis or promotion, but it cannot silently
self-promote model output into established Memory. Promotion may be automatic
only where an explicit deterministic Ada rule for that learning class permits
it; otherwise it requires confirmation. Evidence that has not been promoted
may still be retained in the inspectable learning area under its protection
domain and may support later plausibility checks.

The default file organization should therefore keep established Memory and
learning evidence logically separate inside the same protection domain, for
example:

```text
<protection-domain>/
├── memory/       # established/current authoritative Memory
└── learning/     # observations, observed facts, hypotheses, evidence
```

The exact directory names/file granularity remain implementation choices.
Both areas must remain human-readable; the learning area is not a hidden
secondary truth store.

#### Confirmed initial learning classes

The maintainer confirmed four default **learning-policy classes**. These are orthogonal to the content/evidence roles above: they decide how evidence may be retained/promoted based on risk, not whether something is a preference, fact, observation, or hypothesis. More specific classes may be added later, but they must map back to one of these behaviors rather than silently inventing a new trust level.

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

#### Episodic conversation summaries

Some interactions are valuable because the **conversation itself** provides useful future context even when individual facts have already been extracted.

Ada should therefore support selective episodic summaries for longer or materially useful conversations.

Examples:

- architecture/design interviews;
- planning discussions;
- decisions with rationale and unresolved questions;
- emotionally or operationally important conversations where later continuity matters;
- multi-step problem-solving sessions likely to be referenced later as "we discussed this recently".

A conversation episode should be a compact human-readable Memory artifact, not a raw transcript by default.

Illustrative representation:

```markdown
---
type: conversation_summary
participants:
  - christian
started_at: 2026-09-19T07:57:00+02:00
scope: private
source_ref: optional-conversation-reference
topics:
  - ada
  - permissions
  - learning
---

# Ada architecture interview

## Summary

We clarified that ...

## Decisions

- ...
- ...

## Open questions

- ...
```

Rules:

- not every conversation receives a durable summary;
- summaries should capture decisions, useful context, conclusions, and open loops rather than reproduce the transcript;
- extracted facts/preferences may still live as separate ordinary Memory entries;
- the episode may reference the original conversation where that reference remains available;
- if the original transcript is deleted, the summary may remain according to normal Memory rules;
- later retrieval may use episodic summaries to answer references such as "we talked about this the other day" without loading full historical conversations.

#### Referenced documents and external source material

Ada also needs to remember information **from documents** without requiring every source document to live inside the Git-versioned Markdown Memory.

Examples include:

- school letters;
- contracts;
- invoices;
- forms;
- PDFs and scans;
- notes or records stored in iCloud or another user-controlled file store.

The preferred model to characterize is:

```text
external/user-controlled document
        │
        ├── stable document reference
        └── optional content fingerprint
                 │
                 ▼
         Memory summary / metadata
         (Markdown + YAML)
```

A Memory entry may contain:

- title/document type;
- relevant people/subjects;
- received/document date;
- concise summary;
- extracted deadlines or facts;
- source location/reference;
- optional content hash/fingerprint for change detection;
- privacy scope;
- provenance and lifecycle state.

Illustrative representation:

```markdown
---
type: document_summary
document_type: school_letter
scope: family
document_date: 2026-09-18
source:
  kind: external_file
  uri: <provider-independent reference>
  fingerprint: <optional>
---

# School letter — class trip

## Summary

...

## Relevant dates

- ...
```

The URI/reference format must remain provider-independent at the Memory layer. iCloud may be one concrete storage provider, but Ada should not encode iCloud-specific semantics into the canonical Memory model.

Document handling rules:

- the original document may remain outside Git and outside the Memory vault;
- Ada may retain only a summary/reference when that is sufficient;
- if a task requires the original document, Ada must resolve/access it through the applicable file/provider boundary and permissions;
- a missing/unavailable source must be distinguishable from a deleted/forgotten memory;
- Memory deletion does not automatically delete an externally stored document unless an explicit document-management action is separately authorized;
- document summaries inherit the same privacy/scope rules as other Memory;
- raw document content must not be copied into a broader scope merely for retrieval convenience.

#### Memory selectivity and retention

Ada must not treat every utterance, event, or successful action as durable Memory.

The amount retained should be governed by **usefulness, stability, privacy cost, and evidence**, not by a goal of maximum recall.

Initial principles:

- prefer compact durable facts/preferences/routines over raw interaction history;
- retain selective episodic summaries when the conversation as a whole is likely to provide useful future continuity;
- retain document summaries/references when future tasks need the source context without copying the source document into Memory;
- observations used for learning may be temporary and should be compacted, expired, or discarded when no longer useful;
- repeated equivalent memories should converge rather than accumulate indefinitely;
- low-value incidental details should normally remain session context only;
- sensitive information has a higher bar for durable retention than ordinary low-risk preferences;
- durable Memory should be periodically gardened so the human-readable corpus remains understandable rather than becoming an append-only transcript;
- retention policy may differ by memory class, maturity state, and privacy sensitivity.

The target is **useful continuity, not exhaustive surveillance**.

Exact retention windows and compaction thresholds remain open and should be characterized from representative usage rather than fixed prematurely.

#### Global and per-interlocutor adaptation

Ada may evolve at more than one level, and those levels must remain separable.

At minimum, characterize:

1. **Global Ada personality** — stable traits and interaction principles that apply generally across users;
2. **Per-interlocutor interaction profile** — preferences learned for a specific person, such as desired brevity, terminology, explanation depth, or interaction style;
3. **Domain/routine Memory about that person** — facts, routines, relationships, and preferences that are about the person rather than about Ada's own behavior.

Per-interlocutor adaptation must not silently mutate the global Ada personality.

Example:

```text
Global Ada:
  concise, transparent, privacy-first

Christian interaction profile:
  prefers concise technical answers
  tolerates architecture terminology

Another person:
  prefers simpler explanations
  wants more explicit confirmation
```

Ada may learn and refine both the global personality and per-interlocutor profiles, but:

- global changes require stronger evidence because they affect everyone;
- per-interlocutor adaptations stay inside that person's privacy scope;
- one person's interaction preferences must not leak into another person's profile;
- relationship-specific adaptation remains subordinate to privacy and authority boundaries;
- untrusted content cannot directly rewrite either layer.

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

## Provenance model

Provenance should explain **why Ada believes a memory** without retaining an unnecessary copy of the original source.

**Confirmed rule for direct manual edits:** the current Markdown is the
authoritative content, and its file revision history is sufficient provenance
for the manual edit. Do not require a second claim-level YAML provenance record
for a person to edit a note. The selected versioning mechanism must actually
capture such edits; an unrecorded edit has no historical provenance. Revision
history shows what changed and when it was recorded, but does not by itself
authenticate who made the edit. Ada must not invent an `explicit_user`
confirmation basis or an editor identity from a filesystem event.

For **Ada-extracted or externally sourced claims**, keep enough minimized
evidence to explain why Ada created the claim and to preserve correction or
contradiction history. Characterize a single human-readable claim unit with
its evidence adjacent to it; do not maintain a second semantic copy in YAML.
Exact syntax and required fields remain open. Optional source kinds include:

- explicit user statement;
- direct manual file edit;
- observation / learned outcome;
- calendar or other structured local source;
- email/message source;
- derived from another Memory entry.

Rules:

- provenance is **minimized**; raw chats, emails, or documents are not copied into Memory merely to prove provenance;
- `source_ref` may be omitted or become non-resolvable after source deletion;
- deletion of a source does not by itself invalidate an already established derived memory;
- provenance must never create authority or widen audience;
- cross-scope provenance must not leak private filenames, titles, snippets, or identifiers into a broader scope;
- explicit manual edits remain first-class provenance and must not be treated as inferior merely because Ada did not create them;
- a direct edit does not inherit a previous claim's source link as evidence
  for the newly changed wording; the prior source remains historical;
- superseded/contradicted entries retain enough provenance to explain how the current state was reached.

## Versioning, backup, and sync are separate concerns

The Memory design must treat these as three different mechanisms:

- **versioning** — recover accidental edits and inspect how Memory changed;
- **backup** — recover from device loss/corruption;
- **sync** — replicate current state across authorized devices/users.

Git-like history is attractive for Markdown because it provides diffs and rollback.
If history is used as the provenance for manual edits, Ada must ensure that
out-of-band changes become recorded revisions. This is a requirement on the
eventual versioning adapter, not a claim that the current prototype already
records them.

The maintainer explicitly accepts the following semantic split:

- **Ada forgetting** means Ada no longer reads or retrieves the forgotten content from the current authoritative Memory state or any derived index;
- historical versions may still retain earlier content for recovery/versioning;
- permanent erasure from history/backups is a separate lifecycle/operations concern and may be handled outside Ada.

Therefore Git-style history is **compatible with Ada's runtime forgetting semantics**, provided Ada only reads the current authoritative state during normal Memory retrieval and derived indexes are rebuilt from that state.

Any selected mechanism must still characterize:

- encryption at rest and key ownership;
- per-private-vault versus shared-vault protection;
- operational forgetting from Ada's current readable state and indexes;
- optional historical purge/retention outside normal Ada retrieval;
- retention windows and eventual purge where required;
- recovery if a key/device is lost;
- ability to restore one person's vault without exposing another's;
- offline operation;
- human-inspectable recovery where practical.

Possible solution families to research later include:

- per-vault Git-style versioning, potentially the simplest baseline for inspectable Markdown history;
- encrypted snapshot/version stores;
- filesystem-native snapshots where available;
- encrypted backup tools independent of the live Markdown representation.

The authoritative Memory format should not depend on whichever versioning/backup mechanism is selected.

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

Ada's accepted Memory architecture has three distinct concerns. They may share
files or process boundaries where that stays simple, but their semantics must
not collapse:

1. authoritative human-controlled Memory;
2. inspectable learning evidence/state that can propose changes to Memory;
3. a rebuildable RAG-style retrieval/index layer.

Automatic learning is therefore designed in from the start even when the first
implementation supports only a subset of promotion/aging behavior. Retrieval
optimization is likewise replaceable and must never become an alternate truth
store.

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

### Source/document layer

Authoritative Memory may reference source documents that remain outside the Memory vault.

This source/document layer is **not itself Memory** and is not automatically Git-versioned with Memory. It may live in a user-controlled local filesystem, iCloud, another configured file provider, or a future Ada-managed document store.

Ada's Memory model owns the reference, summary, provenance, and extracted durable knowledge; the source store owns the original bytes and its storage lifecycle.

A future document-storage abstraction should provide at least:

- stable reference/identity where possible;
- read access under explicit scope/authority;
- source availability status;
- optional fingerprint/version observation;
- no assumption that the source is always local or always online.

### 2. Inspectable learning evidence/state

Automatic learning consumes source events, observations and outcomes, but it
must not write model guesses directly into established Memory.

The architecture must preserve at least the semantic distinction between:

- explicit user/source statements;
- observations;
- provisional hypotheses;
- confirmed/established Memory;
- contradicted, superseded, stale, or forgotten state.

Learning evidence and state must remain human-inspectable, scoped to the same
or narrower protection domain as the source, attributable enough to explain
promotion/correction, and unable to grant permission. Exact files/fields,
promotion thresholds, aging rules and compaction are implementation details,
but the distinction itself is architectural.

A first implementation may deliberately defer automatic promotion while still
persisting/representing the above semantics correctly. Later learning logic
must fit this boundary rather than requiring a second opaque truth store.

### 3. Derived RAG retrieval/index layer

This layer exists only to make authoritative Memory efficiently retrievable.
It is conceptually an automatically maintained **cache/index** over the
human-readable source of truth, not Memory authority in its own right.

It may contain:

- full-text indexes;
- embeddings;
- semantic chunks;
- normalized lookup keys;
- explicit link graphs derived from Markdown links;
- semantic or inferred knowledge graphs;
- derived search metadata.

Rules:

- it is reconstructible from authoritative Memory and, where needed, inspectable learning state;
- it is never an independent truth source;
- deleting/rebuilding it must not lose authoritative Memory;
- stale index state must be detectable and repairable;
- it must preserve enough scope metadata that retrieval cannot widen audience/access boundaries;
- forgotten or superseded content must not be returned as current context;
- remote embedding/index services are not part of the default local path;
- inferred graph edges remain derived evidence and never become authoritative Memory merely because an indexer generated them.

The preferred retrieval flow is:

```text
query
  -> determine permitted protection domains
  -> derived retriever/index returns candidate references
  -> re-read current authoritative Markdown for those references
  -> validate scope + current/superseded/unresolved/forgotten state
  -> assemble the minimum relevant model context
```

For very small vaults the retriever can simply be direct file/FTS search. For
larger vaults it may use chunks, embeddings, hybrid search, graphs, or another
RAG implementation behind an Ada-owned retrieval port. The final context must
remain grounded in current authoritative content rather than trusting a stale
cached chunk merely because an index returned it.

This split allows Ada to reuse mature RAG/retrieval technology without giving
an opaque agent-memory database ownership of user truth.

## Hard gates before scoring

A candidate cannot win by weighted score if it fails a hard gate.

| Gate | Requirement |
| --- | --- |
| Human control | Authoritative Memory is human-readable and directly editable without Ada. |
| Open format | The authoritative representation remains usable without a proprietary editor or database runtime. |
| No hidden persistence | No second independent persistent truth store; indexes/caches are reconstructible. |
| Local/offline baseline | Core Memory read/write/retrieval can operate without cloud access. |
| Scope isolation | Individual/private/shared scopes can be represented and enforced without trusting the model. |
| Storage isolation | Read access to one private Memory domain must not implicitly grant read access to other private domains; derived indexes must preserve the same boundary. |
| History privacy | Normal Ada retrieval must not read forgotten historical content; versioning/backups must preserve vault privacy even if older versions remain recoverable outside normal Ada use. |
| Authority separation | Learned Memory cannot create or widen permissions. |
| Correction semantics | Corrections, supersession, contradiction, and deliberate forgetting can be represented safely. |
| Learning explainability | Observations, hypotheses, promotion, correction, and rejection remain inspectable; no hidden behavioral model silently becomes Memory truth. |
| Deletion/export | Users can inspect, export, edit, and delete authoritative memories; derived state can be rebuilt. |
| Provenance | Material facts can retain useful source/reason attribution without requiring raw source retention. |
| License | Runtime/build dependencies must be compatible with Ada's MIT distribution strategy and documented in NOTICE. |
| Maintenance | Fits the accepted Python/container architecture and the project's roughly 1–2 evenings/week maintenance budget. |

## Reference systems and lessons

These systems are not automatically candidates for adoption; they are useful evidence for Memory/document design.

### OpenJarvis

Current architecture documentation describes Memory primarily as persistent searchable document storage with ingestion, chunking, retrieval, and context injection. Available backends include SQLite/FTS5, FAISS, ColBERTv2, BM25, and hybrid retrieval.

Useful lesson for Ada:

- mature document retrieval can remain a replaceable backend capability;
- document source attribution and bounded context injection are valuable;
- Ada should avoid making the retrieval database itself the only authoritative personal Memory if that would sacrifice human-readable ownership.

References:

- https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/overview.md
- https://github.com/open-jarvis/OpenJarvis/blob/main/docs/getting-started/quickstart.md

### Mark LIV

Mark LIV currently stores remembered user facts locally in `memory/long_term.json` and separates storage capacity from prompt budget by recalling additional facts on demand. It also has document-reading/summarization tooling, but its documented persistent personal Memory remains a local JSON store rather than a curated document knowledge base.

Useful lesson for Ada:

- prompt budget and Memory capacity should remain separate;
- visible deletion/inspection of remembered facts is good product behavior;
- the flat personal-fact model is too coarse for Ada's per-person scopes, provenance, lifecycle, and document requirements.

Reference:

- https://github.com/FatihMakes/Mark-LIV

### Hermes Agent

Hermes separates several persistent concerns:

- `SOUL.md` for agent identity/personality;
- `USER.md` for the user profile;
- `MEMORY.md` for learned facts/notes;
- SQLite/FTS5 session storage for full conversation history and search.

Its built-in Markdown Memory is intentionally bounded and injected at session boundaries, while older conversations are retrieved on demand through session search. Hermes also supports optional external Memory providers in addition to the built-in Markdown files.

For documents, current Hermes documentation supports file/context references and temporary document caches, while a persistent user workspace/knowledge-base design is still being discussed separately.

Useful lessons for Ada:

- separating global agent identity, per-user profile, learned Memory, and conversation history is a strong precedent for Ada's global/per-interlocutor model;
- bounded always-in-context Memory plus on-demand historical retrieval validates separating storage from context budget;
- full transcript/session storage can solve recall but is not equivalent to Ada's desired human-readable episodic summaries;
- document storage should be a separate concern from compact personal Memory;
- external Memory providers are useful references, but Ada should keep authoritative user-controlled Memory independent from provider-specific databases.

References:

- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/which-file-does-what.md
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/sessions.md
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory-providers.md
- https://github.com/NousResearch/hermes-agent/issues/531

## Broader Memory/document landscape

The broader ecosystem suggests that Ada should distinguish between **complete assistant references** and **reusable Memory/context components**.

### Additional assistant/reference systems worth tracking

#### Khoj

Khoj is an open-source "second brain" that can search and chat over Markdown, PDF, plaintext, Org-mode, Notion, and other user knowledge, with Obsidian integration and self-hosting.

Useful lesson:

- personal document/notes retrieval can be a first-class assistant capability rather than an upload-only RAG feature;
- existing user knowledge stores should be reusable rather than migrated into an opaque assistant database.

Reference: https://github.com/khoj-ai/khoj

#### Mimir

Mimir combines a local-first assistant, document RAG, persistent conversations, and explicitly human-readable Markdown personal Memory.

Useful lesson:

- human-readable personal Memory plus opaque/reconstructible document retrieval is a viable split;
- this is a close small-scale reference for Ada's Markdown-source-of-truth principle.

Reference: https://github.com/csornyei/mimir

#### PersonalAI

PersonalAI combines continuously synchronized document folders, local OCR, hybrid RAG, an entity knowledge graph, controllable Memory, and explicit security/egress controls.

Useful lesson:

- continuously watched external document folders can remain the source material while indexes/knowledge graphs are derived;
- document deletion/change detection and entity-graph generation can be treated as separate pipelines.

Reference: https://github.com/lucianhanga/personal-ai

### Reusable Memory/context frameworks to evaluate

#### Letta MemFS

Letta's current MemFS is a git-backed Markdown filesystem with YAML front matter. Files under `system/` are always included in context; other files remain discoverable and are loaded on demand. It also supports shared git-backed Memory repositories and background Memory maintenance.

This is one of the closest existing architectural references to Ada's current direction.

Potential reuse question:

- determine whether MemFS components are sufficiently separable from the Letta runtime to reuse behind an Ada-owned boundary; otherwise adopt only the patterns.

References:

- https://github.com/letta-ai/letta-docs-md/blob/main/concepts/memfs/index.md
- https://github.com/letta-ai/letta-code

#### Hindsight

Hindsight provides isolated Memory banks with `retain`, `recall`, and `reflect`; it distinguishes facts/experiences from consolidated observations and supports living "mental models"/knowledge pages. Recall combines semantic, keyword, graph, and temporal retrieval. Current repository license is MIT.

Particularly relevant Ada concepts:

- per-user/per-project banks as protection/relevance boundaries;
- evidence-backed observations instead of flat confidence;
- compact knowledge pages derived from accumulated evidence;
- explicit retain/recall/reflect separation;
- token-bounded hybrid retrieval.

Potential Ada role:

- serious candidate for a **derived learning/retrieval engine**, provided authoritative Markdown can remain Ada-owned and Hindsight state can be rebuilt or treated as non-authoritative.

Reference: https://github.com/vectorize-io/hindsight

#### LangMem

LangMem is an MIT-licensed memory SDK that supports memory extraction, consolidation, update, hot-path management, and background processing. Its core APIs can work with storage systems other than LangGraph's native store.

Potential Ada role:

- investigate reusable write-time learning/consolidation logic while keeping Ada's Markdown/vault abstraction authoritative.

Reference: https://github.com/langchain-ai/langmem

#### Cognee

Cognee turns documents, code, and conversations into a self-hosted knowledge graph plus semantic retrieval layer. The Python package is Apache-2.0.

Potential Ada role:

- derived document/knowledge graph alternative to Graphify/Graphiti;
- useful for comparing graph construction from heterogeneous personal documents and conversations.

Reference: https://github.com/topoteretes/cognee

#### OpenViking

OpenViking unifies resources, memories, skills, and sessions behind a virtual filesystem and has evolved into a substantially closer architectural match for Ada than a generic RAG store.

Relevant current capabilities include:

- user- and peer-scoped Memory namespaces;
- account/user authentication and tenant-aware retrieval;
- shared resources with optional ACLs;
- Memory files such as profile/identity/preferences/entities/events/experiences;
- session commit -> asynchronous Memory extraction and memory-diff/audit artifacts;
- hierarchical L0/L1/L2 context loading;
- filesystem-like read/write/edit/forget/reindex operations;
- local file/vector storage and optional at-rest encryption.

However, its main project/runtime/server is currently **AGPLv3**, so it does not pass Ada's current permissive-runtime license gate.

There is a second mismatch to characterize before treating it as an authoritative-Memory candidate even if licensing changed: OpenViking's supported contract is a server-mediated virtual filesystem/context database, not necessarily Ada's desired ordinary user-owned Markdown/YAML vault with arbitrary out-of-band edits and disposable derived indexes.

Useful concepts to study without adopting the main runtime:

- resources vs Memory vs skills vs sessions as separate context types;
- user vs peer Memory for per-interlocutor adaptation;
- hierarchical directory summaries (coarse-to-detailed context);
- tenant-aware retrieval and ACL patterns;
- session-to-memory consolidation and memory-diff auditing;
- explicit forget/reindex operations.

Current status: **high-value Memory/context architecture benchmark; main runtime blocked by the current license strategy**.

Detailed review: `docs/research/openviking-pizza-bot-fit.md`

Reference: https://github.com/volcengine/OpenViking

#### Supermemory

Supermemory provides document/Memory ingestion and graph-style retrieval and is integrated as an optional Hermes Memory provider. Its current public licensing surfaces require closer review: the repository exposes an MIT LICENSE while recent self-hosted release material also describes product-specific document limits.

Current status: **license/product-boundary review required before Ada runtime consideration**.

Reference: https://github.com/supermemoryai/supermemory

### Emerging synthesis for Ada

The ecosystem increasingly converges on several patterns that align with Ada:

```text
human/source layer
  Markdown / files / documents / sessions
              |
              v
learning/consolidation layer
  extract / reconcile / observe / summarize
              |
              v
derived knowledge layer
  FTS / vectors / graph / temporal indexes
              |
              v
context assembly
  load only the smallest relevant context
```

Ada's differentiator should remain that **the human/source layer and privacy/authority boundaries are Ada-owned**, while mature frameworks may be reused below that boundary.

## Historical candidate matrix (superseded as implementation direction)

This matrix is intentionally **role-aware**. Ada may use one component for authoritative file-native Memory and another for derived learning/retrieval. A candidate that is poor as the source of truth may still be strong behind an Ada-owned boundary.

Legend: ✅ strong fit / 🟡 partial or adapter required / ❓ not yet verified / ❌ structural mismatch.

| Criterion | ReMe | Hindsight | Letta MemFS | LangMem |
| --- | --- | --- | --- | --- |
| Top-level license compatible with Ada MIT strategy | ✅ Apache-2.0 | ✅ MIT | ✅ Apache-2.0 | ✅ MIT |
| Human-readable authoritative files | ✅ Markdown/YAML is source of truth | ❌ bank/database is primary state; Markdown knowledge pages are projections | ✅ git-backed Markdown files | 🟡 storage-agnostic toolkit, not a file-native store itself |
| Human direct edit/correction | ✅ first-class | 🟡 via APIs/export rather than canonical files | ✅ first-class file editing | 🟡 depends on chosen backing store |
| Derived indexes rebuildable from files | ✅ via source-file watcher/recovery lifecycle; `reindex` alone is not a full rebuild | 🟡 observations can be regenerated from retained bank facts, but Ada-owned-file rebuild path is not established | 🟡 MemFS syncs files and agent state; full rebuild semantics need verification | 🟡 depends on backing store |
| Learning / consolidation | ✅ auto-memory / auto-dream / digest refinement | ✅ particularly strong: evidence-backed observations and mental models | ✅ reflection/background memory patterns | ✅ extraction, consolidation, update, hot/background paths |
| Evidence / provenance model | ✅ source links from digest to sessions/resources | ✅ particularly strong supporting-evidence model | 🟡 needs characterization | 🟡 application-defined |
| Per-person/private isolation | 🟡 one workspace per Ada protection domain is plausible; concurrent/enforceable isolation still needs characterization | ✅ strict bank isolation | ❓ agent/repository separation exists; household privacy model not verified | ❌ no isolation model supplied by the library |
| Shared household Memory | ❓ requires Ada-specific design | 🟡 multi-bank composition is client-side; shared bank possible but Ada semantics required | 🟡 shared repositories exist, household semantics still Ada-owned | ❌ must be supplied by Ada |
| Git-native history | 🟡 files are versionable but Git is not the core contract | ❌ | ✅ built in | ❌ |
| Conversation/resource ingestion | ✅ sessions + resources are first-class source layers | ✅ conversations/documents can be retained | 🟡 external memory files/context repos; broader ingestion is runtime-dependent | ✅ conversation-oriented extraction |
| Runtime independence from another agent framework | ❌ current package import/runtime path requires AgentScope in the characterized path; target-Mac spike confirmed this path works with native Ollama | ✅ standalone server/client/embedded options | ❌ tightly coupled to Letta runtime/SDK | 🟡 core primitives are storage-agnostic, but ecosystem is LangGraph-oriented |
| Fit as Ada authoritative Memory substrate in this earlier shortlist | ✅ leading evaluated library | ❌ | 🟡 architecture reference / possible component | ❌ |
| Fit as Ada derived learning/recall layer in this earlier shortlist | ✅ | **✅ strongest evaluated candidate in that round** | 🟡 | ✅ lightweight candidate |

### Earlier working conclusion (superseded by staged MVP direction below)

**Earlier primary deep-dive candidate: ReMe** for the authoritative, human-readable Memory substrate. This historical conclusion predates the Markdown/Git/direct-search control and is not a recommendation to adopt ReMe for the MVP.

Why it led in that round:

- Markdown/YAML files are explicitly the source of truth;
- source/session/resource and long-term-memory layers are already separated;
- keyword/link/vector indexes are derived;
- users can inspect and edit Memory directly;
- it already implements consolidation/refinement rather than only retrieval;
- Apache-2.0 passes the top-level license gate.

Unresolved gates recorded in that round:

1. verify the full runtime/dependency license path, not only ReMe's top-level Apache-2.0 license;
2. decide whether accepting AgentScope as a Memory dependency is compatible with Ada's already accepted PydanticAI runtime boundary, or whether a narrower ReMe integration/decoupling is required;
3. verify out-of-band edit and full watcher-based rebuild behavior under Ada's scenarios (`reindex` alone is insufficient);
4. determine whether separate Ada protection domains can map cleanly to separate ReMe workspaces without cross-scope indexes/state;
5. test correction, contradiction, deletion, episodic summaries, and external document references against Ada's semantics;
6. characterize local-model/Ollama and Python 3.14 behavior on the accepted target platforms.

**Earlier secondary deep-dive candidate: Hindsight** for learning/consolidation and recall, not as Ada's authoritative store.

Its evidence-backed observations, strict banks, temporal/graph/lexical/semantic recall, and mental models are particularly relevant to Ada's learning design. The key question is whether it adds enough value as a rebuildable derived layer to justify operating both ReMe and Hindsight.

**Letta MemFS** was the strongest architecture/reference in that round for Git-backed Markdown context repositories, but runtime coupling made it a weaker adoption candidate.

**LangMem** was the lightweight fallback in that round for reusable extraction/consolidation logic if ReMe's or Hindsight's larger runtimes proved too invasive.

Detailed source findings are tracked in:

- `research/memory/reme/findings.md`
- `research/memory/reme/scenario-matrix.md`
- `research/memory/hindsight/findings.md`

### Candidates currently outside the primary shortlist

- **Basic Memory / OpenViking** — useful design references, but current AGPL licensing conflicts with Ada's runtime license strategy.
- **sqlite-memory** — source-of-truth concept is relevant, but the current Elastic License 2.0 plus additional grant remains a licensing hard-gate concern.
- **Graphify / Graphiti / Cognee** — evaluate as derived graph/retrieval components, not authoritative Memory.
- **Docling** — evaluate separately for document parsing/normalization; it does not compete for the Memory role.

## Candidate architectures

The accepted MVP architecture selects candidate A as the baseline. The remaining candidates are retained as research/reference options or optional derived components and are not required by the MVP.

### A. Ada-owned file-native Memory + optional derived index — accepted baseline

Concept:

- authoritative Markdown notes in a user-controlled Memory directory/vault;
- a simpler MVP baseline uses direct Markdown reads and basic search first,
  with captured per-domain Git history for direct edits; a derived index is
  added only when measured retrieval needs justify it;
- optional YAML properties/front matter only for distinct fields with one canonical representation; manually edited claims need no separate YAML provenance;
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

This control must be measured before selecting a two-component ReMe + LangMem
runtime. ReMe would add a replaceable reader/indexer if ordinary file access
and search fall short; LangMem would add a replaceable semantic proposal helper
only where its correction/learning benefit exceeds the extra dependencies.
Neither component is required to define the authoritative file format.

Risks / work:

- Ada must define the Memory file schema and migration/versioning rules;
- the versioning adapter must capture out-of-band edits; Git commit metadata
  alone does not authenticate a human editor, and past sensitive content
  remains in history until handled under a separate retention policy;
- correction, contradiction, concurrent edit, and index reconciliation semantics are Ada-owned work;
- semantic retrieval quality must be characterized rather than assumed.

This is the accepted baseline architecture. It is selected because it satisfies the human-control and trust-boundary requirements with the smallest mandatory runtime surface. Optional derived components must demonstrate measured value before they are added.

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

Use these scenarios to validate implementations of the accepted architecture. The first real-household Memory slice must at minimum close scenarios 1–5, 7–8, 10, 17–18, 20–21, and 25–27; learning/gardening/episodic scenarios are gated when those features are enabled:

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
18. **Private vault isolation** — a person with legitimate access to one private Memory vault cannot read another person's private vault or a cross-scope derived index.
19. **Shared derivative provenance** — a shared minimized fact can remain attributable without leaking private source content or identifiers.
20. **Version recovery** — an accidental Markdown edit can be restored without weakening scope isolation.
21. **Operational forget with history** — deleting/forgetting a memory removes it from Ada's current retrieval and rebuilt indexes even if a Git/version history still contains an older copy; permanent historical erasure is a separate operational concern.
22. **Selective retention** — incidental low-value details remain session-only while stable useful preferences/routines are compacted into durable Memory.
23. **Per-interlocutor adaptation** — Ada can learn a communication preference for one person without changing global Ada personality or another person's profile.
24. **Conversation continuity** — after a long architecture interview, Ada stores a compact episodic summary and can later retrieve "what we decided two days ago" without loading the original transcript.
25. **Referenced school letter** — Ada stores a summary, deadlines, and a protected reference to a school letter while the original PDF remains in an external user-controlled document store.
26. **Unavailable source document** — a remembered document summary remains usable while Ada clearly reports that the referenced original is currently unavailable.
27. **Source/memory lifecycle separation** — forgetting a document summary removes it from Memory retrieval without silently deleting the original external file.

## Evaluation criteria to weight with the maintainer

After hard gates, candidate scoring should consider:

- human editability / explainability;
- retrieval quality and context/token efficiency;
- correction and contradiction semantics;
- learning quality, explainability, and false-learning resistance;
- selectivity/retention quality and resistance to unbounded Memory growth;
- episodic-summary quality and continuity value;
- document-reference portability and source-lifecycle separation;
- global-versus-per-interlocutor adaptation isolation;
- privacy/scope and physical storage isolation;
- versioning/backup privacy and recoverability;
- local/offline behavior;
- operational simplicity;
- integration effort with current Python/PydanticAI architecture;
- resource use on M1/16 GB;
- portability to later Linux/vServer deployment;
- dependency/security maturity;
- replaceability and data portability;
- ongoing maintenance effort.

Weights were deliberately not assigned in this earlier broad criteria list; the completed historical matrix below used its own frozen weights.

## Implementation and optional research after the architecture decision

1. Define the smallest Ada-owned general Memory semantic model from the scenarios above without turning the vault into a rigid ontology.
2. Characterize **Markdown-first notes with optional non-duplicated YAML properties**; capture manual edits in file history and use separate structured files only where justified by a concrete data type.
3. Characterize structured/property lookup + Markdown links + FTS5 before adding more expensive retrieval infrastructure.
   Measure direct file reads and basic search against ReMe on representative
   vault sizes before requiring any derived index.
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
15. Define the minimal provenance schema and cross-scope provenance redaction/reference semantics.
16. Compare protected storage topologies: per-person private vaults plus shared vaults versus equivalent designs, including OS ACL and encryption options.
17. Define partitioning for FTS/graph/vector indexes so derived retrieval cannot collapse private protection domains.
18. Characterize per-vault Git-style versioning as a baseline, including encryption/privacy, recovery, and the rule that normal Ada retrieval reads current state only.
19. Define optional historical purge/backup-retention semantics separately from Ada's operational forgetting.
20. Define retention/compaction policy by memory class and maturity state so durable Memory stays useful rather than exhaustive.
21. Define the boundary between global Ada personality evolution and per-interlocutor interaction-profile learning.
22. Define when a conversation merits an episodic summary and the minimum summary schema for decisions, rationale, and open loops.
23. Define a provider-independent document-reference abstraction for local files, iCloud, and future stores, including fingerprint/change detection.
24. Decide whether Ada eventually needs a managed document store in addition to references to user-controlled external storage.
25. Characterize Letta MemFS as the closest git-Markdown architecture reference and determine whether any implementation can be reused without adopting the Letta runtime.
26. Characterize Hindsight as a derived learning/retrieval engine, especially banks, evidence-backed observations, knowledge pages, and rebuildability from Ada-owned Memory.
27. Characterize LangMem for storage-agnostic extraction/consolidation logic.
28. Compare Cognee, Graphify, Graphiti, and Hindsight for derived graph/temporal retrieval over representative Memory and document scenarios.
29. Use OpenViking as a design reference for hierarchical context loading and resource/Memory separation; do not adopt the AGPLv3 main runtime under the current license strategy.
30. Keep Memory-derived values distinct from explicit/context-derived values until this ADR defines trustworthy provenance; ADR-0007 intentionally deferred `memory_derived`.

## Executable ReMe evidence

The target-Mac characterization now passes the main substrate/runtime gates:

- Python 3.14 / Apple Silicon install and startup;
- human-readable Markdown/YAML write/read;
- preservation of Ada-owned nested YAML metadata;
- out-of-band edit followed by clean derived-state rebuild;
- operational forget followed by clean rebuild;
- two independent ReMe workspaces with canary isolation;
- direct native Ollama tool calling with `qwen3.5:9b`;
- full local Auto Memory -> Auto Dream workflow, including preference, correction, and contradiction fixtures.

Repeated semantic characterization found a material boundary condition, but not a deterministic correction bug:

- the first ReMe semantic run corrected the Markdown body to Thursday while generated metadata/digest text disagreed or inverted the correction;
- an independent later run corrected Wednesday -> Thursday consistently in both source note and generated description, so the earlier inversion did **not** reproduce;
- that later Auto Dream run extracted three plausible units but integrated 0/3 because generated agent receipts failed validation;
- two explicit contradictory pickup claims remained separate rather than last-write-wins, but ReMe still created no deterministic contradiction relation/state.

Therefore ReMe remained useful research evidence, but under the accepted architecture it may only be considered as an optional derived reader/indexer; its model-generated consolidation cannot be authoritative Ada truth. The missing canonical fact/lifecycle/provenance semantics must be supplied outside ReMe.

That did **not** establish ReMe as an Ada truth engine. The subsequently
added Markdown/Git/direct-search control is the simplest staged MVP
candidate; ReMe, LangMem and Hindsight remain optional research candidates
if they demonstrate a measured benefit beyond that control.

The first shared-fixture comparison provides additional evidence:

- **LangMem** updated the same structured memory ID from Wednesday to Thursday and preserved two unresolved pickup claims as separate records, but invented a synthetic provenance value for the second claim when none was supplied;
- **Letta/MemFS** produced readable Git-backed Markdown with explicit correction and separate conflicting claims, but corrupted/truncated one evidence token and invented another while later claiming verbatim preservation;
- **Hindsight** now has complete fresh-database core evidence. Preference recall is source-backed; explicit Wednesday -> Thursday correction resolves to Thursday while retaining both source facts; bank isolation holds in the tested cross-token queries; direct recall is fast; document forget deletes the source document and its associated memory unit, after which recall is empty. However, its consolidated correction observation invents a validity interval that was never supplied, and its unresolved 16:00/17:00 pickup claims are collapsed into a single preferred 17:00 observation that incorrectly carries the 16:00 evidence token. Therefore Hindsight is promising as a **derived learning/recall layer**, not as Ada's canonical contradiction/provenance truth. Agentic `reflect` also timed out against local `qwen3.5:9b` and remains an optional performance benchmark.

These results strengthen the need to evaluate **semantic correctness and provenance integrity separately** from storage/runtime success.

This historical characterization moved the remaining ReMe-specific research away from basic runtime feasibility and toward:

- comparing ReMe, LangMem, Hindsight, Letta/MemFS, and evidence-backed composite options in the now-historical weighted decision round;
- external document reference/lifecycle fit;
- exact transitive license/security audit;
- maintenance/AgentScope dependency cost;
- whether Hindsight adds enough derived-learning value to justify a second subsystem.

## Decision status

The normative architecture consists of this Decision section, the
**Security and semantic invariants**, the **Hard gates**, and body sections
explicitly marked **Confirmed** (including private-by-default placement,
knowledge/evidence roles and promotion, learning-policy classes,
contradiction/correction precedence, manual-edit provenance, and the
forgetting/history split). Sections marked "to characterize", "Questions still
to decide", candidate/reference surveys, historical matrices and executable
evidence are context or follow-up work, not silently adopted components.

ADR-0008 accepts the following MVP architecture:

- authoritative Memory is **file-native, Markdown-first, human-readable and directly editable** outside Ada;
- a manual edit to the current authoritative file becomes the current content Ada must respect;
- claim/source/lifecycle information that matters to the user stays inspectable with the human-readable Memory and must not be duplicated into a second drifting claim truth store;
- ordinary new personal knowledge is private by default, and private/shared scopes map to **enforceable protection domains**, not merely folders or model-interpreted tags;
- authoritative Memory, version history/backup/sync, derived retrieval indexes, permissions, and action truth remain distinct mechanisms;
- runtime access to protected Memory domains is mediated by an Ada-owned **host-side Memory Broker**; the long-lived Ada runtime/model does not receive standing access to all household vaults;
- normal retrieval starts with current authoritative files and the simplest sufficient local search; derived indexes/graphs/vector layers are optional, rebuildable, scope-preserving accelerators rather than independent truth sources;
- operational forgetting removes content from Ada's current readable state and derived retrieval; historical purge/backup retention is a separate lifecycle/operations concern;
- corrections, contradictions, provenance, maturity and confirmation basis remain visible enough for deterministic validation and safe conflict handling;
- evidence origin, durable Memory kind, and lifecycle/maturity are separate dimensions; established Memory is logically separated from inspectable learning evidence, with an explicit Ada-owned promotion/assimilation boundary;
- the confirmed learning-policy classes A–D are normative: low-risk explicit knowledge may be remembered privately with provenance, inferred patterns observe first, sensitive/consequential knowledge requires confirmation or a future explicit rule, and secrets/credentials are never ordinary automatically learned Memory;
- evidence precedence is normative and not last-write-wins: explicit user confirmation/correction outranks observational patterns, while ambiguous conflicting explicit claims remain unresolved;
- every model-originated Memory write or promotion passes a deterministic Ada-owned validation boundary for source/trust, private-by-default scope, learning class/sensitivity, provenance/lifecycle, and contradiction/correction handling before it becomes authoritative;
- untrusted/quoted/model-generated content cannot directly rewrite trusted established Memory; it can only enter the evidence/proposal path under the applicable conservative learning rule;
- an inspectable change-history/versioning mechanism that records observed out-of-band edits is an architectural requirement for manual-edit provenance; Git-style per-domain history is only the leading adapter candidate, not the requirement itself;
- automatic learning is architecture-relevant from the first slice: explicit statements, observations, hypotheses and established Memory remain semantically distinct, while concrete promotion/aging algorithms may be added incrementally;
- the RAG/retrieval layer is an automatically rebuildable cache/index over current authoritative Memory; candidate hits are re-grounded in current source content before entering model context;
- source documents may remain in external user-controlled stores and be referenced by Memory rather than being silently copied into the Memory vault;
- ReMe, LangMem, Hindsight, Letta/MemFS, vector stores, graph stores and similar frameworks are **not required MVP layers**. They may be added only behind Ada-owned boundaries when representative evidence justifies their runtime, privacy and maintenance cost;
- `Memory != Permission`, `Memory != Action Truth`, and `Authoritative Memory != Derived Index` remain architecture invariants.

Git-style per-protection-domain history is the leading MVP **versioning adapter candidate**, not an authentication or security boundary. Its exact capture/concurrency/recovery mechanism must be validated before product use.

The protection-domain access topology delegated by ADR-0003 is now decided:
Ada uses a **host-side Memory Broker** as the storage-access boundary for the
MVP. The broker mediates vault access and exposes only the domain(s) required
for the current authenticated/authorized task; the Ada runtime/model must not
receive a standing mount or credential set for all private/shared household
Memory. Exact IPC, ACL/encryption/key mechanics and broker process structure
remain implementation details. Authorized users must still be able to
access/edit their own authoritative Memory directly in plain human-readable
form without depending on Ada.


This acceptance chooses the architecture boundary and the smallest baseline. It does **not** claim that the Memory service, protection domains, versioning adapter, retrieval quality, learning lifecycle, or historical purge operations are already implemented or production-ready.

The executable four-candidate characterization is complete. The **historical weighted decision matrix** lives at:

`research/memory/comparison/decision-matrix.md`

The matrix criteria and weights were frozen **for the completed research scoring run** before candidate scoring: five deliberately non-overlapping criteria at 20% each — Authoritative Memory fit, Semantic correctness & provenance, Privacy & isolation, Retrieval & learning quality, and Architecture & operational fit. This does not accept those weights as the final product decision or allow retrospective rescoring of the historical run. Any revised decision matrix needs a separately recorded rationale and a fresh comparison including the control. License compatibility remains a hard gate; `Memory != Permission` remains an architecture invariant.

Scoring is now complete. The decision-eligible results are:

- **ReMe + LangMem: 78/100**
- **ReMe: 72/100**
- **ReMe + Hindsight: 72/100**

LangMem and Hindsight are not decision-eligible standalone authoritative architectures because neither provides Ada's required human-readable source of truth. Letta/MemFS remains not decision-ready from current evidence because provenance failed and forget/isolation were not characterized.

Among the **scored** options, the current matrix points to ReMe as the file-native reader/indexer with LangMem as an optional semantic-change proposal helper. The simpler Markdown + captured history + basic-search control is unscored. A backend decision must compare it before requiring either added component. Hindsight remains an optional later derived-learning/retrieval layer if representative real-world retrieval tests justify its operational cost.

This historical scoring remains decision evidence; it does not override the accepted simpler baseline or require a scored framework dependency.

A dependency-free [Markdown/Git/direct-search control](../../research/memory/control/README.md)
now exercises the same synthetic preference, correction, contradiction, and
direct-edit cases. It succeeds at reading current files after a direct edit,
preserving separate conflicting notes, and detecting a change in Git diff.
Its explicit capture step is not an automatic watcher. Deleting a note removes
it from direct search while retaining historical versions, as permitted by
the versioning/forgetting split above. A future derived index must likewise
exclude forgotten content. Separate repositories under the same OS identity
do not enforce household privacy. Its search relevance and scale remain
unmeasured. No numeric score or Memory-backend selection follows from this
small control run.

Any fresh comparison must price the Ada-owned work needed to make this control
safe in practice, including edit capture, concurrency handling, scoped commits,
source retirement, section-aware retrieval, isolation, and purge semantics.
The control is not zero-cost merely because it has no runtime dependency.

For this accepted MVP architecture, add ReMe only when representative retrieval/indexing
evidence justifies its AgentScope dependency; add LangMem only when a bounded
semantic proposal helper demonstrably outperforms the simplest safe Ada-owned
validation path. Revisit the direction if the control fails required scenarios.

### ReMe + LangMem final-fit boundary

This historical integration boundary applies only if a fresh comparison later
justifies ReMe + LangMem against the simpler control. It is not the current
MVP implementation plan.

Source/dependency review narrowed the leading composite further:

- use pinned `reme-ai[as]==0.4.1.12`; AgentScope is effectively required by ReMe's import graph even though it is packaged as an optional extra;
- do **not** use `reme-ai[core]`;
- do **not** expose ReMe's unauthenticated/wildcard-CORS HTTP service as an Ada boundary;
- run ReMe out of process over **stdio MCP**, with an initial read-only allowlist (`version`, `status`, `search`, `read`);
- keep authoritative writes Ada-owned and file-native; ReMe observes/indexes the vault;
- use LangMem only for typed semantic proposals whose schema excludes provenance, privacy scope, authority, permission, lifecycle state, and validity windows;
- attach source references and lifecycle state deterministically in Ada after proposal validation;
- enforce patched dependency floors for LangMem's broad ecosystem (`langchain-core>=1.3.3`, `langgraph>=1.0.10,<2`, `langgraph-checkpoint>=4.1.1`);
- do not use LangGraph persistence, LangSmith, or cloud model providers for this Memory role.

The combined executable gate under `research/memory/reme-langmem/` **passed on the target Mac** (2026-09-23, head `be34013`). The pinned dependencies installed together with Ada; the stdio tool allowlist, synthetic correction and conflict handling, silent-overwrite rejection, and retrieval after an out-of-band file edit passed. `pip-audit` reported zero known vulnerabilities for the dependencies it listed. The research [fit review](../../research/memory/reme-langmem/findings.md) records the raw-run limitations: this is a single synthetic vault; the fixture repeats source/history metadata in YAML and Markdown, which a production schema must avoid; the Friday edit also leaves old source references without new Friday provenance, an issue that persists even without duplicate fields. Metadata-level license triage is not a redistributed-wheel audit. This is evidence for the candidate, not adoption or a general proof of semantic integrity.

A second target-Mac run (2026-09-23, head `fde552f`) passed both the YAML
comparison lane and the new **Markdown-only** lane. The latter repeated the
synthetic preference/correction/conflict/overwrite/edit checks with source
references adjacent to the current claim and no claim YAML. Its scripted
direct edit removed the obsolete source line and was captured by a local Git
diff; ReMe read/search returned the edited Markdown. This does not prove
automatic capture of real user edits, human identity, forgetting, protection
domain enforcement, or retrieval quality at scale. Dependency-path triage
places `psycopg` and `psycopg-binary` in Ada's reconstructed DBOS baseline,
`certifi` in its PydanticAI baseline, and newly attributes `bidict` to ReMe's
AgentScope tree and `orjson` to LangMem's LangSmith tree. The installed macOS
`psycopg-binary` package includes several native libraries; their exact
redistribution obligations remain open. See the fit review for paths and
artifact evidence. No license distribution clearance is claimed.

## Production and implementation gates after architecture acceptance

The architecture above is accepted independently from any one Memory framework or versioning implementation. Before Ada stores real household Memory or claims a production-ready Memory service, the implementation must still close the following gates:

1. validate the file-native control against representative retrieval/edit/forget scenarios on the target platform and measure retrieval quality/scale before adding a derived search framework; before custom retrieval infrastructure, run a focused reuse comparison of credible local RAG/retrieval components (at minimum the SQLite FTS5 baseline and suitable modular/embedded candidates such as LlamaIndex Core, Haystack, LanceDB, or an equivalent maintained option) behind an Ada-owned retrieval port;
2. implement safe out-of-band edit capture and Ada writes, including path-restricted history capture, same-file concurrency detection/reconciliation, Git/file lock handling, crash recovery, and explicit stale-source handling;
3. implement and validate the accepted host-side Memory Broker topology plus enforceable per-person/shared domains and scope-partitioned retrieval/indexes; bind each broker request to trusted actor/audience/authorization context, fail closed on scope ambiguity, and prove that the Ada runtime cannot read domains outside the current authorized request;
4. make current/superseded/unresolved retrieval semantics deterministic enough that obsolete or contradictory text is not promoted as current truth; fail closed when lifecycle/currentness is ambiguous rather than asking the model to infer it;
5. ensure forgetting removes content from current authoritative retrieval and every reconstructible derived index, while keeping historical purge/backup retention as a separately explicit operation;
6. define and validate the minimum provenance/source-reference and external-document lifecycle needed by implemented MVP scenarios without creating duplicate hidden truth;
7. route every model-originated Memory write/promotion through the deterministic Ada-owned validation boundary (source/trust, private-by-default scope, learning class/sensitivity, provenance/lifecycle, contradiction/correction) before authoritative persistence;
8. if a dependency-backed derived layer is selected, complete its license/security/dependency review and target-platform validation before adoption; release artifacts require their own distribution review.

Historical candidate scores may be revisited only if they are reused as decision evidence. A failure of Git, direct search, ReMe, LangMem, Hindsight, or another concrete implementation should trigger replacement behind these accepted boundaries rather than reopening the human-controlled source-of-truth architecture by default.

Where an explicit correction requires explaining the old statement without
consulting Git history, an illustrative **single Markdown note** can place
the current statement and its source under "Current", and the replaced
statement and its original source under "Superseded (not current)".
Retrieval must not promote the superseded section back to a current fact.
The direct-search control does not satisfy that requirement: substring search
still finds superseded text, so section-aware retrieval/context assembly is an
explicit open gate. For competing unconfirmed statements, use an "Unresolved"
section with both claims and their sources; ask for clarification rather than
selecting one. This is a proposed human-readable convention, not a parser or
implemented write path. A direct manual edit that changes a claim but leaves
an old source cannot silently count as a sourced new claim.

Operational Memory gates remain open. Before any Ada-originated write, capture
out-of-band changes separately from Ada's own commit and restrict the commit
itself to the intended path (for example with a path-restricted commit or a
separate verified index); path-scoped staging alone is insufficient because
unrelated pre-staged changes can otherwise enter the commit. Detect changed
content before overwriting, and treat file/Git lock failures as a stopped
operation requiring reconciliation; merely comparing a hash before an
unprotected rename cannot close a concurrent editor race. Concurrency also
runs in the other direction: a stale editor buffer may overwrite Ada's latest
write. Ada must capture its own write promptly enough that a later manual
revert remains detectable, while manual edits remain authoritative current
content.

A claim changed without its source being reviewed needs validation or an
explicit unknown/stale-source marker. Keep mutually unresolved claims together
and visibly unresolved in current Markdown; the two-file control fixture only
demonstrates retention. Section-aware retrieval/context assembly is required
before "Superseded" or "Unresolved" conventions can safely coexist with direct
text search.

Narrowing a shared scope to private may stop future current-state sharing but
cannot revoke content already read, synced, copied, backed up, or retained in
shared history. Ada must present that limitation explicitly. Historical purge
and reader revocation are separate policies/operations; they are not a
precondition that permanently forbids scope narrowing. No narrower household
scope is accepted implicitly by this ADR.
