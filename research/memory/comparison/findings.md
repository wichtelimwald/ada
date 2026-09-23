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

No semantic result yet.

Four sandbox attempts have exposed harness/image prerequisites rather than Hindsight Memory semantics:

1. the first attempt timed out while the initial ONNX embedding model was still downloading;
2. after extending readiness and reusing the downloaded model, Hindsight initialized embeddings and verified the local Ollama connection, but embedded PostgreSQL (pg0) failed because the generic `python:3.14-slim` sandbox lacked `libgssapi_krb5.so.2`;
3. after adding that runtime library, pg0 reached `initdb` but failed because the container was executed with the host UID (501) and that UID had no passwd entry inside the image;
4. after adding the matching passwd user, PostgreSQL started, but pg0 returned `uri=None`; Hindsight then rejected the missing DB URL before migrations.

The fourth failure was traced to pg0's current Unix process-liveness check: pg0 invokes the external `ps` command, while Debian/Python slim images do not include it by default. Without `ps`, pg0 can start PostgreSQL but misclassify the process as not running and expose no URI.

These are Linux sandbox prerequisites, not host requirements and not Hindsight semantic failures.

The Hindsight lane now builds a dedicated disposable research image that:
- installs the required Kerberos GSSAPI runtime library;
- installs `procps` so pg0's `ps`-based process check works;
- creates a non-root passwd-visible user matching the maintainer's host UID/GID;
- preserves host ownership of repo-local result artifacts.

With those prerequisites fixed, the next run reached actual Memory operations:
- retain/consolidation completed;
- direct recall completed quickly (roughly 90 ms for preference and 37 ms for correction);
- recall preferred consolidated observations over superseded raw facts;
- Hindsight's agentic `reflect` call timed out against local `qwen3.5:9b` after several Ollama read timeouts and is therefore treated as an optional performance benchmark, not part of the common semantics gate.

That run is **not used as final semantic comparison evidence** because repeated resume attempts had reused the same pg0 instance; logs showed duplicate accumulated memories (for example 2 pending memories in a one-item isolation bank). Retries now use a fresh pg0 instance while preserving only the venv/model cache.

The host and persistent Dev Container remain unchanged.

## Current comparison interpretation

The evidence currently supports distinct strengths rather than a winner:

| Candidate | Strongest observed fit | Material concern |
| --- | --- | --- |
| ReMe | file-native authoritative substrate, edit/rebuild/forget/isolation | model consolidation is nondeterministic / can fail validation |
| LangMem | structured correction and unresolved-conflict handling | no authoritative store; invented provenance in one fixture |
| Letta/MemFS | Git-backed human-readable memory + readable correction/conflict representation | evidence-token corruption/invention; runtime coupling |
| Hindsight | pending executable semantics | sandbox prerequisites exposed by first-start model setup and pg0 system-library dependency |

Do **not** conclude that Ada should implement a custom semantic engine from these results. The next evidence needed is Hindsight's completed semantic lane, then the agreed weighted decision matrix.
