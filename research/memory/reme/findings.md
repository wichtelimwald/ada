# ReMe deep dive for Ada Memory

- **Status:** Research in progress
- **Date:** 2026-09-21
- **Upstream:** https://github.com/agentscope-ai/ReMe
- **Purpose:** Determine whether ReMe can serve as Ada's file-native Memory substrate behind Ada-owned privacy, learning, and authority boundaries.

## Executive summary

ReMe is currently the strongest candidate for Ada's human-readable Memory substrate, but adoption is **not yet justified**.

The strongest matches are:

- Markdown/YAML files are explicitly the durable source of truth.
- `metadata/` is derived state.
- conversations, resources, daily summaries, and consolidated long-term memory are separate layers.
- provenance is represented through source links.
- default retrieval is BM25 plus wikilink expansion; embeddings are optional.
- manual/out-of-band file editing is a supported workflow.
- automatic consolidation already supports CREATE / CORROBORATE / REFINE / CORRECT.

Material Ada gaps found so far:

- ReMe has one configured `workspace_dir` per Application and no built-in household privacy/authority model.
- its HTTP/MCP service has no general-purpose user authentication; Ada must own access mediation.
- ReMe's Python package is more tightly coupled to AgentScope than its optional-dependency layout initially suggests.
- resource ingestion expects source files to be copied into the workspace under `resource/`; Ada's desired external-document-reference model needs an adapter/extension.
- `reme reindex` does not rescan files, rechunk, or rebuild the wikilink graph; full source-of-truth reconstruction relies on the watcher/startup ingestion lifecycle.
- ReMe consolidation does not implement Ada's explicit observed/provisional/confirmed/stale lifecycle or Ada's deterministic contradiction/authority semantics.

Current interpretation: **continue the deep dive; do not adopt yet**.

## 1. License and dependency path

### Upstream license

ReMe declares and ships **Apache-2.0**.

This passes Ada's top-level permissive-license gate.

### Python requirement

ReMe declares:

```text
requires-python = ">=3.11"
```

No upper bound is declared. Python 3.14 compatibility remains unverified until an executable characterization is run.

### Base dependencies

The current base package declares ordinary Python runtime dependencies including:

- aiofiles
- croniter
- FastAPI
- FastMCP
- httpx
- loguru
- mistletoe
- numpy
- openai
- psutil
- pydantic
- python-frontmatter
- PyYAML
- rich
- uvicorn
- watchfiles
- zstandard

A full transitive-license audit is still required before adoption.

### AgentScope coupling

ReMe declares AgentScope as an optional extra:

```toml
as = [
  "agentscope[model-ollama]==2.0.7.post1",
]
```

AgentScope itself is Apache-2.0.

However, ReMe source contains unconditional AgentScope imports in core modules including:

- `reme/steps/base_step.py`
- `reme/steps/evolve/_evolve.py`
- `reme/steps/evolve/auto_memory.py`
- `reme/steps/index/_source_format.py`
- `reme/components/as_llm/`
- `reme/components/as_embedding/`

The upstream packaging smoke test explicitly installs `reme-ai[as]` before testing `import reme`.

Therefore the practical runtime dependency is currently stronger than "optional AgentScope integration" suggests.

**Ada implication:** treat AgentScope as part of the likely ReMe runtime path until proven otherwise. Do not assume a small standalone file/index library can be imported without it.

### `core` extra

The much larger `core` extra additionally pulls in:

- Claude Agent SDK
- OpenAI Codex SDK
- proxy tooling
- FAISS
- zvec
- Neo4j
- NetworkX
- Polars
- ReMe Studio
- image support and other packages

Ada should **not** default to `reme-ai[core]`. If ReMe is adopted, select the smallest dependency path that satisfies characterized Ada requirements.

## 2. Authoritative data model

ReMe's core invariant is "Memory as File, File as Memory".

Workspace layers:

```text
source records -> session/ + resource/
working memory -> daily/
long memory    -> digest/
system state   -> metadata/
```

Relevant properties:

- `daily/`, `digest/`, sessions, and resources are ordinary user-owned files.
- long-term memory is Markdown with YAML frontmatter.
- wikilinks encode explicit relationships.
- `metadata/` contains catalogs, chunks, indexes, and graph snapshots.
- metadata is not intended as the human editing surface.
- files can be read, written, moved, corrected, and deleted directly.

This strongly matches Ada's human-controlled Markdown direction.

### ReMe vs Ada directory semantics

ReMe's directories primarily encode **memory lifecycle/layer**:

- session
- resource
- daily
- digest/personal
- digest/procedure
- digest/wiki

Ada also needs **privacy protection domains**:

- person-private
- shared-household
- Ada/global

These are orthogonal concerns.

A single ReMe workspace must therefore **not** be assumed to equal the entire household Memory.

Most plausible characterization path:

```text
Ada protection domain
   -> one ReMe workspace
   -> that workspace's own metadata/indexes
```

For example:

```text
private-person-a -> ReMe workspace A
private-person-b -> ReMe workspace B
shared-household -> ReMe workspace shared
```

Whether multiple ReMe Applications can be operated efficiently in-process is still to be characterized.

## 3. Security and access boundary

ReMe's file operations have useful containment properties:

- paths are resolved against the workspace;
- path traversal outside the workspace is rejected;
- `~` expansion is deliberately rejected;
- request-scoped `_allowed_paths` can constrain write/edit operations and fails closed on invalid constraints;
- per-path in-process locks protect read-modify-write cycles.

However, the service boundary is explicitly local/trusted:

- default bind is `127.0.0.1`;
- CORS permits any origin;
- Jobs can write/move/delete files;
- no general-purpose user authentication exists.

ReMe documentation explicitly warns not to expose the service directly to the public internet.

**Ada implication:** ReMe cannot own person/audience/authority decisions. Ada must decide which protection-domain workspace is accessible before ReMe is invoked.

### Agent permissions

The default AgentScope wrapper config uses:

```yaml
permission_mode: bypass
```

This does not automatically mean arbitrary filesystem authority: the ReMe jobs expose bounded tool sets and workspace/path checks exist.

Nevertheless, Ada must not delegate its authority model to this wrapper. The accepted invariant remains:

```text
Learned != Authorized
Memory != Permission
```

## 4. Human/out-of-band edits and reconstruction

Manual editing is a first-class ReMe workflow.

The background `index_update_loop` watches `daily/` and `digest/` Markdown and handles added/modified/deleted changes.

Deletion through ReMe causes the watcher to prune affected chunks from vector/keyword/graph projections.

### Important nuance: `reindex` is not a full source rebuild

`reme reindex`:

- rebuilds BM25 and/or embeddings from already-ingested chunks;
- does **not** scan the workspace;
- does **not** rechunk files;
- does **not** rebuild the wikilink graph from source files.

Upstream recovery guidance instead says to preserve source files, isolate/remove damaged `metadata/`, restart, and let watchers rebuild.

**Ada implication:** a deterministic Ada "rebuild derived Memory from authoritative files" operation should wrap/test the full startup/watch ingestion path rather than merely invoking `reindex`.

Required characterization:

1. edit a digest Markdown file while ReMe is stopped;
2. remove derived metadata;
3. restart;
4. verify file chunks, BM25, graph, tags, and optional embeddings match current source files;
5. verify deleted/forgotten current content is not retrievable.

## 5. Conversations and episodic memory

Auto Memory stores:

```text
conversation
 -> session/dialog/<session-id>.jsonl
 -> daily/<date>/<topic>.md
 -> optional later digest via Auto Dream
```

Daily notes are deliberately distilled rather than transcript-shaped.

This maps well to Ada's episodic-summary requirement.

Notable source filtering:

- tool-result blocks are omitted from the saved source conversation;
- base64 data blocks are omitted;
- daily memory records preferences, key facts, decisions/rationale, current state, and reusable experience.

### Ada gap

Ada has an explicit retention/product decision around raw message archives and episodic summaries.

ReMe normally retains the filtered source conversation JSONL as evidence.

Ada must therefore decide per protection domain whether ReMe's `session/` should:

- be retained directly;
- be subject to Ada's message/archive retention policy;
- be disabled/replaced so only the episodic summary and minimized provenance survive.

## 6. Learning and consolidation

Auto Dream processes recent changed daily Markdown and extracts a limited number of reusable units.

The default flow:

```text
changed daily files
 -> extract reusable units
 -> recall existing digest nodes
 -> CREATE / CORROBORATE / REFINE / CORRECT
 -> digest
```

Strong matches for Ada:

- repeated evidence can corroborate an existing memory;
- refinement can add scope/conditions/exceptions;
- correction can handle conflicting evidence;
- source paths are retained as provenance;
- digest nodes are intentionally compact abstractions rather than copies.

### Contradiction behavior

The current integration prompts explicitly allow conflict annotation such as:

```text
> note: contradicted by [[<path>]] - <one-line>
```

and direct the integration agent to tighten a claim to what old and new evidence jointly support.

This is better than simple last-write-wins.

### Ada gap: learning maturity

ReMe does not currently expose Ada's required lifecycle as a first-class semantic contract:

```text
observed
 -> provisional
 -> confirmed
 -> stale / contradicted / superseded
```

Nor does it distinguish confirmation basis such as:

```text
explicit_user
observed_pattern
```

ReMe's `CORROBORATE` may "strengthen confidence", but this remains prose/prompt-driven rather than Ada's deterministic human-readable state model.

**Ada implication:** either:

1. extend ReMe frontmatter and consolidation prompts with Ada-owned lifecycle fields and validation; or
2. keep Ada learning-state records above ReMe and use ReMe only to materialize/search summaries.

This is a major deep-dive decision point.

## 7. External documents/resources

ReMe's current source-resource model is:

```text
workspace/resource/<source-file>
 -> Auto Resource
 -> daily card
 -> optional digest
```

The original source file is copied/placed inside the ReMe workspace.

Text formats are the primary current fit; images have a separate processor.

### Ada mismatch

Ada's desired model also supports:

```text
external document in iCloud/local provider
 -> stable provider-independent reference
 -> Memory summary/provenance
```

without necessarily copying the original into the Memory Git repository.

ReMe does not currently provide that provider-independent external-reference model as its ordinary resource path.

Potential adapter approaches to characterize:

- **materialize-on-ingest:** Ada keeps authoritative external URI, temporarily/materially copies into ReMe `resource/`;
- **summary-only:** Ada feeds normalized content to ReMe while preserving its own external provenance reference;
- **custom ReMe resource processor:** introduce an Ada reference resource type that resolves content under Ada's provider/security boundary.

The canonical document identity must remain Ada-owned if this is adopted.

## 8. Retrieval and context cost

Default retrieval is deliberately relatively light:

- BM25 keyword index;
- wikilink graph expansion;
- optional vector embeddings disabled by default.

Search can also use tags and dates.

This aligns with Ada's direction to characterize lexical/link retrieval before adding vector infrastructure.

Positive design point: the vector stack is not mandatory for the default path.

### Graph semantics

ReMe's graph is primarily an **explicit wikilink graph**, not a semantic inferred graph such as Graphify/Graphiti.

This means Graphify/Hindsight/Cognee may still add value as optional derived layers if representative Ada queries need inferred relationships.

## 9. Multi-user and protection-domain fit

Current ReMe configuration has one `workspace_dir` per Application.

No built-in semantics were found for:

- Person != Data Subject != Audience != Authority;
- private-to-shared minimized derivatives;
- household grants;
- cross-vault query authorization.

This is expected to remain Ada-owned.

Promising property: a workspace naturally keeps its source files and metadata/indexes together, so **one ReMe workspace per Ada protection domain** may give clean index isolation.

Still required:

- characterize multiple workspaces concurrently;
- ensure no shared/global cache merges indexes;
- measure resource overhead;
- define cross-vault federated retrieval in Ada without copying private content into shared indexes.

## 10. Local models / Ollama

ReMe pins the AgentScope extra:

```text
agentscope[model-ollama]==2.0.7.post1
```

so Ollama is a supported upstream model path.

However, the default ReMe config uses an OpenAI-compatible model component and default cloud-oriented model settings.

Ada must explicitly supply its accepted local model boundary/configuration and test that no unexpected egress is required.

## 11. Current gate assessment

| Ada gate | ReMe assessment | Notes |
| --- | --- | --- |
| Human-readable authoritative Memory | PASS | Strong core design |
| Open file format | PASS | Markdown/YAML/JSONL |
| Derived indexes not authoritative | PASS | Explicit upstream design |
| Local/offline storage | PASS | File/index operations local |
| Local LLM path | CONDITIONAL | Ollama supported through AgentScope; characterize end-to-end |
| Human out-of-band editing | PASS/CHARACTERIZE | Supported; full rebuild uses watcher lifecycle, not just `reindex` |
| Private/shared scope isolation | ADA LAYER REQUIRED | One workspace can be one protection domain |
| Authority separation | ADA LAYER REQUIRED | ReMe is not an authorization engine |
| Learning lifecycle | PARTIAL | Strong consolidation, missing Ada maturity contract |
| Contradiction semantics | PARTIAL | Conflict annotation exists; Ada deterministic rules missing |
| Provenance | PASS/PARTIAL | Strong file source links; cross-scope minimization remains Ada-specific |
| Episodic summaries | PASS/PARTIAL | Daily cards good fit; raw session retention policy differs |
| External document references | GAP | Ordinary resource path copies source into workspace |
| Operational forgetting | PASS/CHARACTERIZE | current-source deletion + index pruning; verify rebuild |
| Top-level license | PASS | Apache-2.0 |
| Full dependency license path | OPEN | AgentScope Apache-2.0; full transitive review still required |
| Python 3.14 / arm64 | OPEN | requires-python >=3.11 only; execute later |
| Maintenance fit | PROMISING | substantial reuse, but AgentScope coupling may increase footprint |

## 12. Next work that does not require the maintainer's Mac

1. finish direct/transitive license triage for the minimal ReMe + AgentScope/Ollama path;
2. inspect ReMe's workspace/watch/index code for multi-Application isolation and rebuild guarantees;
3. map Ada's 27 Memory scenarios to ReMe native / adapter / gap;
4. compare ReMe's learning semantics directly against Hindsight;
5. define the thinnest possible `AdaMemoryPort -> ReMe` boundary;
6. identify a minimal characterization configuration that avoids the `core` extra;
7. prepare executable spike cases for later local macOS/Python 3.14 validation.

## First macOS execution — 2026-09-21

The first executable characterization ran on the target macOS/Apple-Silicon/Python-3.14 environment.

Observed PASS results:

- preflight;
- isolated virtual-environment creation;
- pinned `reme-ai[as]==0.4.1.12` installation;
- initial ReMe service startup;
- basic Markdown write/search;
- preservation of nested Ada YAML metadata;
- one-workspace status capture;
- out-of-band Markdown edit;
- clean startup after removing derived metadata;
- search rebuilt from the edited current source;
- operational forget remained forgotten after a clean metadata rebuild;
- second ReMe workspace startup;
- two-workspace canary isolation;
- independent status capture for both workspaces.

This is strong evidence for the file-source, rebuild, forget, Python-3.14, and workspace-isolation hypotheses.

### Initial local-LLM step was a harness defect, not yet a ReMe result

The first `local-llm-memory-flow` invocation failed immediately before useful model characterization.

Source review identified the harness defect: ReMe converts raw messages through AgentScope's `Msg` model, whose `name` field is required. The initial synthetic messages contained only `role` and `content`.

The harness has been corrected to include sender names, and a focused `resume-llm.sh` retry path was added so the successful installation/workspaces can be reused.

Therefore the first LLM failure is classified as:

```text
HARNESS INVALID / RETRY REQUIRED
```

not as a ReMe gate failure.

### Second local-LLM attempt reached the agent but hit the harness HTTP timeout

After fixing the missing AgentScope message `name`, the focused retry progressed through:

- ReMe startup;
- Auto Memory message validation;
- session JSONL persistence;
- daily-note lookup;
- entry into the AgentScope `user_message_create` agent call.

The client then timed out while the service log still showed the agent call in progress and no ReMe/model exception.

This is currently classified as a second **harness limitation**, not a ReMe failure: ordinary HTTP calls used a fixed 20-second timeout, which is too short for a local 9B model plus tool-calling Memory workflow.

The harness now uses:

- 300 seconds for each Auto Memory call;
- 600 seconds for Auto Dream;
- a fresh ReMe workspace for each focused retry, while reusing the already-installed virtual environment.

The next retry should determine whether the local Ollama/AgentScope tool path completes successfully or exposes a genuine runtime/model compatibility issue.

## Third local-LLM attempt — functional success plus performance finding

The corrected long-timeout retry reached real local ReMe/AgentScope/Ollama execution.

Observed behavior:

- explicit preference Auto Memory completed successfully and created a daily note;
- a new "music lesson Wednesday 17:00" fact completed successfully and created a daily note;
- the subsequent explicit correction found the existing note and successfully executed the required `read` tool;
- the client then timed out before the next edit/update tool step completed.

This proves that the local OpenAI-compatible Ollama path and ReMe tool-calling workflow are functional on the target machine. The remaining issue is performance/operational fit for the default ReMe agent configuration, not basic compatibility.

### Default workflow is oversized for Ada's Memory use case

ReMe's published default configuration currently allows:

- `max_tokens: 65536` for the LLM component;
- `max_iters: 30` for the AgentScope ReAct loop;
- an additional `auto_tag_step` after every `auto_memory` call;
- an additional `auto_tag_step` after `auto_dream`.

On the target local 9B model, successful small Memory creates took minutes, and the derived auto-tag pass contributed substantial extra latency.

Tagging is not an ADR-0008 hard gate and can be rebuilt/derived separately.

The characterization harness now includes a bounded Ada profile:

```text
max_tokens      4096
context_size    32768
ReAct max_iters 8
auto_memory     AutoMemoryStep only
auto_dream      extract + integrate + finish, no AutoTag
max dream units 5
```

This is not a production decision. It tests whether ReMe's core Memory semantics are operationally viable when configured to Ada's expected workload rather than ReMe's general-purpose defaults.

## Current recommendation

Keep **ReMe as the primary deep-dive candidate**, but downgrade the earlier assumption that it is a largely standalone runtime-independent library.

The likely decision is not simply "adopt ReMe". The realistic options are:

1. **ReMe substrate + Ada policy/lifecycle adapter**;
2. **borrow ReMe file/layer model but implement a smaller Ada-owned file/index path**;
3. **ReMe file substrate + Hindsight-derived learning/recall**, only if the operational cost is justified.

No option is selected yet.
