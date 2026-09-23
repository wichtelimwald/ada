# ReMe executable characterization plan

- **Status:** Prepared; not yet executed
- **Date:** 2026-09-21
- **Target:** macOS Apple Silicon, Ada's current Python 3.14 environment
- **Purpose:** Resolve the remaining ReMe gates with the smallest realistic dependency path.

## Guardrails

This spike is research only.

It must not:

- wire ReMe into Ada production code;
- modify Ada's accepted PydanticAI runtime architecture;
- install ReMe's `core` extra;
- enable cloud LLM/provider credentials;
- put real personal/private information into fixtures;
- merge or accept ADR-0008 automatically.

Use synthetic canary data only.

## Prepared executable harness

The first macOS characterization is implemented under:

```text
research/memory/reme/mac/
├── README.md
├── run.sh
└── driver.py
```

Run from the Ada repository root with:

```bash
sh research/memory/reme/mac/run.sh
```

The harness deliberately installs ReMe into an isolated temporary virtual environment and writes all workspaces/results outside the repository. It does not change Ada's `pyproject.toml` or production runtime.

The first executable baseline pins the current published ReMe release `0.4.1.12`. Source-level research in this ADR also inspected newer upstream `main` state; do not conflate unreleased upstream behavior with the executable baseline.

The harness currently automates C1-C7 plus the core local-learning part of C9 and dependency metadata capture for C11. C8 (external document reference adapter) and the ReMe-vs-Hindsight part of C10 intentionally remain unimplemented until earlier results show they are decision-changing.

## Environment under test

First attempt:

```text
reme-ai[as]
AgentScope pinned by ReMe
Ollama local endpoint
Ada's current Python 3.14 / macOS arm64
```

Record:

- Python version;
- resolved ReMe version;
- resolved AgentScope version;
- resolved Ollama client version;
- full dependency lock/list;
- install/build failures;
- binary wheels vs local compilation;
- process RSS and startup time.

If Python 3.14 fails, do **not** silently downgrade Ada. Record the incompatibility and only then run a comparison environment on upstream's supported Python baseline to distinguish an Ada-platform issue from a ReMe functional issue.

## C1 — Import and minimal startup

Goal: establish actual framework coupling and platform compatibility.

Checks:

1. install `reme-ai[as]` into an isolated environment;
2. `import reme`;
3. instantiate/start the minimum local application configuration;
4. verify no `core`-only packages are needed;
5. capture dependency tree and errors.

Pass:

- clean import/start on Ada target platform;
- no undeclared cloud credential requirement;
- no `core` dependency leakage.

## C2 — Local-only model path

Goal: prove automatic Memory can run with Ada's local-model posture.

Setup:

- Ollama local endpoint only;
- no OpenAI/Anthropic/DashScope keys;
- outbound network blocked where practical.

Exercise:

1. feed synthetic conversation;
2. run Auto Memory;
3. run Auto Dream/consolidation;
4. inspect generated session/daily/digest artifacts.

Pass:

- expected Memory pipeline works locally;
- no hidden cloud dependency/egress;
- failures are explicit/fail-closed.

## C3 — Human edit + clean derived rebuild

Goal: prove files are truly sufficient source state.

Exercise:

1. create Memory through ReMe;
2. verify retrieval;
3. stop service;
4. manually edit Markdown;
5. move/delete `metadata/`;
6. restart;
7. wait for watcher/startup ingestion;
8. verify BM25, wikilink graph, tag/catalog state reflect only current files.

Also prove that `reme reindex` alone is not mistaken for this full rebuild.

Pass:

- current Markdown deterministically restores derived retrieval state.

## C4 — Operational forget

Goal: prove Ada-style current-state forgetting.

Exercise:

1. write a unique canary fact;
2. verify recall;
3. delete/remove the authoritative current Memory representation;
4. verify immediate recall absence;
5. remove/rebuild all derived metadata;
6. verify canary remains absent.

Git history is explicitly out of scope for normal retrieval.

Pass:

- forgotten current content cannot reappear from derived state.

## C5 — Two protection-domain workspaces

Goal: test the proposed mapping `one Ada protection domain -> one ReMe workspace`.

Create:

- workspace A with canary `ALPHA_PRIVATE_...`;
- workspace B with canary `BETA_PRIVATE_...`;
- optional shared workspace S.

Exercise:

- run both applications/workspaces;
- search/read each;
- inspect metadata paths;
- inspect process/global state;
- attempt accidental cross-workspace path/reference access.

Pass:

- no cross-workspace retrieval;
- no shared global derived index containing both canaries;
- resource overhead remains acceptable.

Record RSS for 1, 2, and 3 workspaces.

## C6 — Correction vs contradiction

Goal: observe native ReMe behavior before Ada overrides it.

Cases:

A. explicit correction:
```text
"Music lesson is Wednesday."
"No, not Wednesday — Thursday."
```

B. unresolved contradiction:
```text
"Pickup is at 16:00."
"Pickup is at 17:00."
```

Inspect:

- daily files;
- digest update;
- source links;
- whether ReMe narrows/reconciles/annotates;
- whether old claim remains inspectable.

Expected result:

- ReMe behavior is evidence for Ada adapter design, not a pass/fail against Ada's final lifecycle.

## C7 — Ada lifecycle metadata coexistence

Goal: see whether Ada-owned YAML fields survive ReMe read/edit/consolidation.

Add synthetic front matter such as:

```yaml
ada:
  state: provisional
  confirmation_basis: observed_pattern
  subject: person-a
```

Run ReMe search and relevant update/consolidation paths.

Pass:

- unknown Ada metadata is preserved;
- ReMe does not silently overwrite/remove it;
- Ada can validate/update it independently.

This is a critical adapter feasibility check.

## C8 — External document reference adapter

Goal: test Ada's desired source lifecycle without moving the canonical original into Git Memory.

Use a synthetic PDF outside the ReMe workspace.

Prototype:

1. Ada-side record owns a provider-independent source reference;
2. materialize or normalize content temporarily for ReMe;
3. generate a Markdown summary containing the Ada-owned source reference;
4. remove temporary/materialized source;
5. verify summary remains retrievable;
6. mark source unavailable and verify Memory remains distinguishable from source availability.

Pass:

- ReMe does not need to own canonical document identity.

## C9 — Episodic conversation summary

Goal: validate conversation continuity without requiring full transcript injection later.

Exercise:

1. feed a long synthetic design conversation;
2. produce daily/episodic summary;
3. ask a later relative-reference query such as "what did we decide in that design discussion?";
4. measure retrieved context size vs source transcript size.

Record:

- summary quality;
- decisions/open-loops preservation;
- source provenance;
- token reduction.

## C10 — Context/retrieval benchmark

Representative questions should test:

- exact facts;
- paraphrased preferences;
- relationships;
- temporal references;
- contradictions;
- conversation episodes;
- source-document summaries.

Compare incrementally:

1. ReMe BM25 + wikilinks;
2. ReMe optional embeddings only if needed;
3. later Hindsight derived recall only on scenarios where ReMe is materially weak.

Do not add Hindsight merely because it scores slightly better. Improvement must justify a second substantial subsystem.

## C11 — Dependency/security/license capture

From the exact successful environment capture:

- resolved package tree;
- package versions;
- license metadata;
- package/source URLs;
- wheels/binaries and architecture;
- vulnerability scan;
- all model licenses/terms.

Any non-permissive, unknown, or conditional runtime artifact blocks adoption pending review.

## Exit criteria

After C1–C11 classify ReMe as exactly one of:

### A — Adopt as Memory substrate

Use ReMe behind Ada-owned ports/policy if:

- target platform works;
- workspace isolation is sound;
- rebuild/forget is reliable;
- Ada YAML lifecycle metadata coexists safely;
- dependency footprint is acceptable;
- license/security gates pass.

### B — Borrow architecture, implement smaller Ada substrate

Choose this if ReMe's file model is good but AgentScope/dependency/operational coupling is disproportionate.

### C — Reject

Choose this if file-source claims fail under rebuild/forget/isolation, required metadata cannot coexist, or license/security/platform gates fail.

No result may change ADR-0008 to Accepted without a separate explicit maintainer decision.
