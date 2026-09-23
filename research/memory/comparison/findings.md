# Memory candidate comparison — executable findings

- **Status:** Research in progress
- **Date:** 2026-09-22
- **Scope:** ReMe 0.4.1.12, LangMem 0.0.30, Hindsight 0.10.1, Letta Code/MemFS 0.32.15
- **Model baseline:** local `qwen3.5:9b`

This document records executable behavior only. It is not a ranking or backend decision.

## ReMe

Operationally strong for the file-native substrate:

- Markdown/YAML source files;
- out-of-band editing and clean derived-state rebuild;
- current-state forget followed by rebuild;
- separate-workspace isolation;
- local Ollama tool path.

Semantic behavior is not fully deterministic across independent runs.

Earlier characterization:
- explicit correction updated the Markdown body to Thursday but generated description/digest text contradicted or inverted the correction.

2026-09-22 comparison run:
- explicit correction remained consistently Thursday in both note body and generated description;
- unresolved pickup claims remained separate;
- Auto Dream extracted three semantically plausible units, but integrated **0/3** because the agent receipts failed validation.

Interpretation:
- the earlier correction inversion is **not reproducible as a deterministic ReMe bug**;
- model-generated consolidation still cannot be treated as authoritative because outputs vary across runs and the integration path can fail after extraction;
- ReMe remains strongest here as a human-readable substrate, not as the sole truth/lifecycle engine.

## LangMem

The structured manager performed very well on the core semantic fixtures:

- preference extracted into an atomic structured record;
- explicit correction updated the **same memory ID** from Wednesday to Thursday;
- the unresolved 16:00 and 17:00 pickup claims remained as two separate records.

Material provenance issue:
- the second conflict fixture contained no evidence token, but LangMem generated a synthetic `SESSION_...` value in the required evidence field.

Interpretation:
- LangMem is the strongest executable evidence so far for reusable structured update/conflict semantics;
- it does not provide Ada's desired authoritative human-readable store;
- its outputs still require provenance validation, and correction-history preservation must be supplied by the surrounding store/journal if required.

## Letta Code / MemFS

The local Git-backed MemFS lane completed and produced human-readable Markdown.

Positive:
- preference persisted;
- Wednesday was explicitly marked overridden by Thursday;
- both pickup claims were preserved as unresolved/separate;
- the resulting files are directly inspectable.

Material provenance integrity failure:
- one preference token was reformatted (`MEMCMP Pref_5E39C2`);
- the original correction token was truncated (`MEMCMP_CORR_A1D88`);
- the second conflict claim was assigned an invented `+ADDENDUM_...` evidence token;
- a generated status file then claimed that evidence tokens were preserved verbatim.

Interpretation:
- Letta/MemFS is a strong architecture reference for Git-backed human-readable memory;
- this run does **not** pass Ada's provenance-integrity requirement without additional validation/constraints;
- forget and protection-domain isolation remain uncharacterized.

## Hindsight

The fresh-database comparison now provides usable core semantic evidence.

Positive:

- explicit preference recall is correct and source-backed;
- explicit correction resolves the current music lesson to **Thursday 17:00** while retaining both Wednesday and Thursday source facts;
- bank isolation holds in the tested direction: cross-bank token queries return only memories from the queried bank, not the other bank's canary;
- direct recall is fast on the small characterized dataset (roughly 20–40 ms after model-side retain/consolidation work);
- observations retain links to source fact IDs, and source facts retain document/source metadata.

Material semantic concerns:

1. **Invented temporal semantics on correction**
   - the consolidated Thursday observation adds a validity interval from 2026-09-23 to 2026-12-31;
   - no such interval exists in the fixture.

2. **Unresolved contradiction is incorrectly collapsed**
   - raw source facts correctly preserve pickup 16:00 and pickup 17:00 as separate documents;
   - the preferred observation collapses them into a single pickup-at-17:00 memory;
   - that 17:00 observation also carries the evidence token from the 16:00 claim.

This is a material Ada hard-gate issue: Hindsight's observation consolidation is useful as a **derived interpretation**, but it cannot define Ada's authoritative contradiction/provenance semantics.

3. **Reflect performance**
   - agentic `reflect` repeatedly timed out against local `qwen3.5:9b`;
   - it is now an optional Hindsight-specific performance benchmark, not part of the common Memory semantics gate.

4. **Forget harness bug, not backend finding**
   - the fresh run reached `forget_before`, but the harness then called Hindsight's async-only low-level Documents client through a fresh `asyncio.run()`;
   - the generated aiohttp session belongs to the client's existing loop machinery, so the call failed with `Timeout context manager should be used inside a task`;
   - the harness now exercises the documented HTTP DELETE endpoint directly and persists `forget_before` before deletion.

Interpretation:

- Hindsight is a strong candidate for **derived learning/recall**, evidence-backed observations, and bank-scoped retrieval;
- it is **not suitable as Ada's canonical conflict/provenance truth layer without validation**, because its consolidation may reconcile ambiguity and invent temporal/provenance details;
- a final focused retry is needed only to close the forget scenario, not to re-establish correction/conflict behavior.

The host and persistent Dev Container remain unchanged.
## Current comparison interpretation

The evidence currently supports distinct strengths rather than a winner:

| Candidate | Strongest observed fit | Material concern |
| --- | --- | --- |
| ReMe | file-native authoritative substrate, edit/rebuild/forget/isolation | model consolidation is nondeterministic / can fail validation |
| LangMem | structured correction and unresolved-conflict handling | no authoritative store; invented provenance in one fixture |
| Letta/MemFS | Git-backed human-readable memory + readable correction/conflict representation | evidence-token corruption/invention; runtime coupling |
| Hindsight | derived observations/recall with source-fact links and bank isolation | collapses unresolved contradiction; invents temporal/provenance details; DB-primary; local Reflect too slow |

Do **not** conclude that Ada should implement a custom semantic engine from these results. The only remaining Hindsight execution gap is the forget endpoint after fixing the harness call; after that, build the agreed weighted decision matrix.
