# Hindsight deep dive for Ada Memory

- **Status:** Research in progress
- **Date:** 2026-09-21
- **Upstream:** https://github.com/vectorize-io/hindsight
- **Purpose:** Benchmark Hindsight against ReMe for Ada's learning, consolidation, isolation, and recall requirements.

## Executive summary

Hindsight is **not a fit for Ada's authoritative human-readable Memory store**, because its primary truth is database-backed.

It is, however, currently the strongest investigated candidate for a **derived learning/consolidation and recall layer**.

Particularly relevant strengths:

- strict Memory-bank isolation;
- explicit `retain` / `recall` / `reflect` separation;
- evidence-backed observations with proof counts and source-memory lineage;
- observation evolution under supporting, contradictory, and extending evidence;
- freshness/staleness awareness;
- preserved observation history;
- mental models / knowledge pages as maintained higher-level syntheses;
- semantic + keyword/BM25 + graph + temporal retrieval;
- token-bounded context assembly;
- local LLM providers including Ollama;
- MIT top-level license.

Material Ada mismatches/costs:

- PostgreSQL/embedded-pg0-style database is authoritative, not Markdown/YAML;
- substantial operational/dependency footprint relative to Ada's MVP;
- raw source facts/chunks are normally retained in the bank;
- Hindsight's contradiction reconciliation still synthesizes an updated belief rather than implementing Ada's deterministic `contradicted` state contract;
- using both ReMe and Hindsight would create two substantial systems and must justify its maintenance cost.

Current interpretation: **excellent benchmark and possible derived layer; do not use as authoritative Ada Memory**.

## 1. License and runtime

Hindsight's root repository and current Python packages declare **MIT**.

The current `hindsight-api-slim` package:

- requires Python >=3.11;
- supports local providers as well as hosted providers;
- documents macOS Apple Silicon and Linux ARM64 support;
- has an embedded deployment option using pg0;
- can also run against PostgreSQL.

The runtime dependency set is materially larger than ReMe's file/index core and includes database, telemetry, multiple model-provider, document-conversion, object-storage, and security-pinned dependencies.

Notable current dependencies include:

- asyncpg / SQLAlchemy / Alembic / pgvector / psycopg2;
- LiteLLM;
- OpenTelemetry packages;
- MarkItDown for document conversion;
- FastAPI / FastMCP;
- Anthropic / OpenAI / Google / Cohere provider clients;
- optional local ML and llama.cpp stacks.

The project contains careful Python 3.14/macOS notes around LiteLLM packaging, but Ada still needs its own executable acceptance test.

**Ada implication:** top-level licensing is favorable, but the operational/dependency footprint is significant. A full transitive-license audit would be required before adoption.

## 2. Memory model

Hindsight distinguishes:

- **world facts**;
- **experiences**;
- **observations**;
- **mental models / knowledge pages**.

Its three primary operations are:

- `retain` — ingest/store information;
- `recall` — retrieve relevant memory;
- `reflect` — reason/synthesize across memory.

This separation is useful for Ada even if Hindsight is not adopted.

## 3. Evidence-backed observations

Observations are Hindsight's strongest match to Ada's learning goals.

They are:

- deduplicated;
- built from multiple facts;
- linked to specific source memories;
- associated with a `proof_count`;
- refined rather than overwritten as evidence changes;
- history-preserving;
- freshness-aware.

The consolidation engine can:

- create observations from novel facts;
- reinforce/refine them with supporting evidence;
- reconcile contradictory evidence;
- rebuild observations after source-memory deletion.

This is materially more explicit than ReMe's prompt-level CREATE/CORROBORATE/REFINE/CORRECT workflow.

### Important mismatch with Ada

Hindsight still does not implement Ada's exact semantic lifecycle:

```text
observed
 -> provisional
 -> confirmed
 -> stale / contradicted / superseded
```

or Ada's separate confirmation basis:

```text
explicit_user
observed_pattern
```

When evidence conflicts, Hindsight's default behavior is to reconcile the history into a richer/current observation.

Ada intentionally requires some conflicts between credible explicit claims to remain unresolved as `contradicted` until clarified.

Therefore Hindsight cannot own Ada's final truth/lifecycle semantics unchanged.

## 4. Freshness and aging

Hindsight has a useful concept Ada should learn from:

- an observation may become **stale** relative to newer unconsolidated memories;
- `reflect` verifies stale observations against raw facts before relying on them;
- mental models likewise track whether relevant newer knowledge has arrived.

This differs from Ada's planned category/time-based aging of observed routines, but the underlying design principle is strong:

> staleness should alter how derived knowledge is trusted, not silently delete it.

## 5. Mental models and knowledge pages

A mental model is a maintained answer/document over a bank.

Properties relevant to Ada:

- it is refreshed when relevant source knowledge changes;
- scope controls both what it may read and where it is visible;
- previous content versions and grounding evidence are retained;
- refresh can be incremental rather than full regeneration.

Knowledge Pages expose these synthesized documents in a navigable tree and can export them as Markdown.

This resembles Ada's desired:

- episodic/subject summaries;
- maintained person/household knowledge pages;
- Memory gardening / consolidation outputs.

But the Markdown is a **projection/export**, not the canonical source of truth.

## 6. Bank isolation

Hindsight Memory Banks are a strong architectural reference for Ada protection domains.

Upstream explicitly documents banks as isolated stores with no cross-bank leakage. Contributor security guidance treats bank isolation as a hard invariant and requires `bank_id` scoping for multi-bank data access.

This maps naturally to:

```text
private person A -> bank A
private person B -> bank B
shared household -> bank shared
```

However, if Hindsight is only a derived layer, Ada should still treat its Markdown vault/workspace as authoritative and reconstruct or repopulate the bank when needed.

A derived bank must never become the only surviving copy of a durable Ada memory.

## 7. Retrieval

Hindsight recall combines four strategies:

1. semantic/vector;
2. keyword/BM25;
3. entity/relationship graph;
4. temporal search.

Results are fused and reranked, then packed to a token budget.

This is a mature implementation of the context-efficiency problem Ada is trying to solve.

Particularly useful concepts:

- token budget is separate from search depth;
- graph and temporal paths are first-class rather than bolted on;
- observations can be preferred over raw facts;
- source chunks may optionally be returned only when more nuance is required.

### ReMe comparison

ReMe default:

- BM25;
- explicit wikilink graph;
- optional vectors.

Hindsight:

- richer inferred entity/relationship graph;
- temporal retrieval;
- vector + lexical fusion;
- reranking;
- evidence-strength signal.

Therefore Hindsight is stronger as a **derived recall engine**, but also substantially heavier.

## 8. Documents

Hindsight can retain documents and raw chunks, and its current runtime includes MarkItDown-based document conversion.

This is useful for retrieval but does not solve Ada's canonical external-document-reference requirement by itself.

If used as a derived layer, Ada should continue to own:

- external document identity/URI;
- privacy scope;
- source lifecycle;
- permission to access original bytes.

Hindsight would receive only material permitted for that bank/protection domain.

## 9. Rebuildability and source ownership

This is the central concern for an Ada integration.

Hindsight can export/import banks and regenerate embeddings in migration flows, but the bank's source facts/documents are still stored in Hindsight.

That is different from ReMe's explicit "files are source of truth, metadata is derived" model.

For Ada, a Hindsight integration should be accepted only if we can define one of these contracts:

1. **fully rebuildable derived bank** — regenerate the bank from authoritative Ada files/source summaries;
2. **selective derived cache** — store only reconstructible facts/observations with no unique user truth;
3. reject Hindsight if essential learning state would become non-reconstructible database truth.

This must be proven in a spike before adoption.

## 10. ReMe vs Hindsight for learning

| Concern | ReMe | Hindsight | Ada implication |
| --- | --- | --- | --- |
| Authoritative representation | Markdown/YAML files | Database bank | ReMe fits source-of-truth requirement |
| Raw evidence | session/resource/daily files | facts/documents/chunks | both retain evidence differently |
| Consolidated belief | digest node | observation | Hindsight has stronger explicit evidence model |
| Supporting evidence count | mostly source links / prompt semantics | first-class proof count | Hindsight stronger |
| History of belief evolution | Git possible externally / source links | first-class observation history | Hindsight stronger |
| Contradiction handling | CORRECT / annotate contradiction | reconcile/refine observation | neither equals Ada deterministic conflict contract |
| Staleness | no equivalent Ada lifecycle contract found | freshness-aware observations/models | Hindsight stronger |
| Isolation | workspace-level; Ada must compose | strict bank isolation | Hindsight stronger derived-domain primitive |
| Retrieval | BM25 + links + optional vectors | semantic + BM25 + graph + temporal + rerank | Hindsight stronger, heavier |
| Human direct edit | first-class | not canonical | ReMe decisive advantage |
| Rebuild from human files | designed around files | not established as primary contract | ReMe decisive advantage |
| Runtime footprint | moderate, but AgentScope-coupled | substantial DB/ML/provider stack | ReMe likely simpler |
| Top-level license | Apache-2.0 | MIT | both pass |

## 11. Candidate composition

The most compelling combined architecture to test is:

```text
Ada authoritative vault
Markdown/YAML
      |
      +--> ReMe
      |    file/watch/digest/explicit-link capabilities
      |
      +--> optional Hindsight derived bank
           observations + hybrid/temporal recall
```

But this is only attractive if Hindsight provides **materially better recall/learning** on representative Ada scenarios.

Operating both by default would violate Ada's maintenance philosophy unless measurable benefit justifies the complexity.

Therefore the preferred evaluation order is:

1. characterize ReMe alone;
2. characterize ReMe + Ada-owned lifecycle metadata;
3. benchmark Hindsight only on scenarios where ReMe remains weak;
4. add Hindsight only if the improvement is substantial.

## 12. Current recommendation

- **Authoritative Memory:** Hindsight = NO.
- **Learning/retrieval benchmark:** Hindsight = YES.
- **Default derived dependency:** not yet.
- **Possible optional advanced derived layer:** promising.

No architecture decision is made by this research note.
