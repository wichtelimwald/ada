# ReMe + LangMem final fit review

- **Status:** Final executable gate pending
- **Date:** 2026-09-23
- **Candidate role split:** ReMe authoritative file substrate + LangMem semantic-change proposal helper
- **Pinned characterization versions:** ReMe 0.4.1.12, AgentScope 2.0.7.post1, LangMem 0.0.30, langchain-ollama 1.1.0

This review narrows the scored ADR-0008 option into the smallest architecture that Ada would actually run.

## 1. ReMe packaging and runtime boundary

### AgentScope is effectively required

ReMe 0.4.1.12 declares AgentScope under the optional `as` extra:

```text
reme-ai[as] -> agentscope[model-ollama]==2.0.7.post1
```

However, ordinary ReMe package bootstrap imports `reme.steps`, and `reme.steps.base_step` imports `agentscope.model.ChatModelBase` at module import time.

Therefore Ada must **not** assume that bare `reme-ai==0.4.1.12` is a usable reduced runtime. The characterized dependency is:

```text
reme-ai[as]==0.4.1.12
```

Do **not** install `reme-ai[core]` for Ada. The core extra additionally pulls capabilities such as Claude/Codex agent SDKs, FAISS, zvec, Neo4j, Polars, Studio, image support, and other integrations that are outside the selected MVP role.

This packaging mismatch is an upstream maintainability concern but not a blocker if ReMe is isolated behind an Ada-owned boundary.

### Do not use ReMe HTTP as Ada's trust boundary

ReMe 0.4.1.12 documents that its HTTP service:

- binds to `127.0.0.1` by default;
- allows CORS from any origin;
- has no general-purpose user authentication;
- can expose jobs that write, move, and delete files.

For Ada, loopback alone is not an acceptable authorization boundary for private household Memory.

### Selected ReMe boundary: stdio MCP subprocess

ReMe's MCP service supports `transport=stdio`; in that mode it does not bind a host/port.

Ada's intended integration is therefore:

```text
Ada / AdaGuard
      |
      | choose allowed protection domain
      v
ReMe subprocess for that vault
      |
      | stdio MCP only
      v
read/search/index over that vault
```

Initial tool allowlist:

- `version`
- `status`
- `search`
- `read`

Not exposed:

- `write`
- `edit`
- `move`
- `delete`
- `auto_memory`
- `auto_dream`

This deliberately prevents ReMe's agent/model workflows from becoming an alternate canonical-write or permission path.

The filesystem/vault remains authoritative. ReMe observes and indexes it.

## 2. LangMem dependency and lifecycle boundary

LangMem 0.0.30 is MIT licensed and storage-agnostic, but its base package has a broader dependency footprint than Ada needs for the selected feature.

Its direct package dependencies include LangChain/LangGraph infrastructure plus provider/observability packages such as:

- `langchain`
- `langchain-core`
- `langchain-openai`
- `langchain-anthropic`
- `langgraph`
- `langgraph-checkpoint`
- `langsmith`
- `trustcall`

Ada uses only the structured Memory-manager path plus `langchain-ollama`.

This is a maintenance/attack-surface cost and is why LangMem remains behind a narrow replaceable port rather than becoming Ada's runtime foundation.

### Security floors

LangMem's own dependency ranges are too broad to serve as Ada's security constraints.

The final characterization enforces at least:

```text
langchain-core >= 1.3.3
langgraph >= 1.0.10,<2
langgraph-checkpoint >= 4.1.1
```

These floors exclude known 2026 unsafe-deserialization ranges.

The final executable run also performs `pip-audit` against the resolved external dependency set and records the exact installed versions.

### No LangGraph persistence for Ada Memory

LangMem is not allowed to introduce a second authoritative Memory store.

For the selected role:

- no LangGraph checkpoint database is authoritative;
- no LangGraph server/auth layer is used;
- no LangSmith service is required;
- no OpenAI/Anthropic provider is used;
- the model endpoint is local Ollama;
- model inputs are minimized typed semantic content, not arbitrary serialized application structures.

## 3. Minimal Ada-owned deterministic boundary

The prior LangMem fixture exposed one critical lesson: when provenance was modeled as an LLM-generated field, LangMem invented a `SESSION_...` value.

The selected architecture removes that capability **by construction**.

LangMem's proposal schema contains only semantic fields:

```text
kind
subject
statement
```

It does not contain:

```text
source/provenance
privacy scope
audience
authority
permission
lifecycle state
validity interval
```

Those remain caller/Ada-owned.

### Explicit correction

Input:

```text
authoritative existing fact
+ new source observation
+ caller-established explicit_correction=true
+ caller-selected correction target
```

LangMem may propose the semantic replacement.

Ada accepts it only if:

- the target is the caller-selected existing memory;
- the subject does not change;
- the proposal matches the explicit correction;
- no extra semantic record is silently introduced.

Ada then attaches the real source references and lifecycle metadata before writing Markdown.

### Non-correction contradiction

When `explicit_correction=false`:

- an existing conflicting explicit claim must not be removed or rewritten;
- a second contradictory claim may be proposed as a new fact;
- Ada owns the resulting `contradicted` lifecycle state;
- a silent overwrite is rejected.

### Authority and scope

LangMem never receives the capability to grant authority or widen Memory scope.

The flow remains:

```text
semantic proposal
      |
deterministic Memory validation
      |
AdaGuard / protection-domain decision
      |
authoritative Markdown write
```

`Memory != Permission` remains unchanged.

## 4. Compatibility with Ada's accepted architecture

### PydanticAI

No replacement.

PydanticAI remains Ada's agent runtime. LangMem is a specialized helper behind an Ada-owned semantic-proposal boundary. ReMe runs out of process.

### DBOS

No overlap.

Memory extraction/validation does not become durable-action truth. Any future durable Memory-maintenance workflow can use DBOS through Ada-owned application semantics if required.

### AdaGuard / Cedar

No replacement.

AdaGuard selects whether a protection domain may be accessed before Ada starts/uses the corresponding ReMe boundary. ReMe does not authorize users.

### Runtime topology

Preferred MVP topology:

```text
Ada Python process
  - PydanticAI
  - DBOS
  - Cedar/AdaGuard
  - LangMem semantic proposal adapter
          |
          | local model
          v
        Ollama

Ada-managed ReMe subprocess
  - AgentScope dependency remains isolated here
  - stdio MCP
  - read/search allowlist
  - one authorized vault boundary at a time
```

A separate LangMem worker is not justified unless the combined dependency test exposes conflicts or future operational evidence demands isolation.

## 5. Supply-chain observations

### ReMe

Positive:

- Apache-2.0;
- PyPI 0.4.1.12 uses Trusted Publishing;
- PyPI provides a GitHub Actions provenance attestation tied to the release commit;
- project is actively maintained.

Concern:

- AgentScope is an effectively required dependency despite being packaged as an optional ReMe extra;
- ReMe pins AgentScope 2.0.7.post1 rather than the newest AgentScope release;
- this requires explicit upgrade review rather than unconstrained updates.

Reviewed AgentScope advisories found for legacy `<=1.0.18` do not include the pinned 2.0.7.post1 version. Separate newer upstream security issues still reinforce the choice to avoid AgentScope tools/MCP-client surfaces that Ada does not need.

### LangMem

Positive:

- MIT;
- source repository remains active and has received 2026 dependency/security maintenance.

Concerns:

- latest published package remains 0.0.30 from 2025;
- PyPI shows a single maintainer and the release was not uploaded through Trusted Publishing;
- package dependencies are broader than the selected semantic-helper role.

Mitigation:

- exact lock/pins in Ada;
- security floors above;
- Dependabot/audit after adoption;
- narrow adapter with no LangGraph persistence or cloud-provider use;
- keep LangMem replaceable.

## 6. Final executable gate

The repository contains:

```text
research/memory/reme-langmem/
  README.md
  config.yaml
  driver.py
  run.sh
```

The run tests the real combined dependency set:

```text
Ada current package
+ ReMe 0.4.1.12 / AgentScope 2.0.7.post1
+ LangMem 0.0.30
+ langchain-ollama 1.1.0
```

and captures:

- `pip check`;
- exact `pip freeze`;
- `pip inspect`;
- runtime package count/size;
- license metadata inventory;
- security floors;
- `pip-audit`;
- stdio read-only ReMe tool surface;
- valid correction;
- unresolved conflict preservation;
- silent-overwrite rejection;
- caller-owned provenance;
- ReMe recall after accepted write;
- out-of-band Markdown edit -> ReMe re-index.

## 7. Current decision gate

No new blocker has been found in source-level review.

The ReMe + LangMem option can move toward ADR selection **only if the final combined run confirms**:

1. Ada + ReMe + LangMem resolve cleanly under Python 3.14;
2. no unresolved high-severity vulnerability exists in the selected dependency graph;
3. transitive license inventory contains no unacceptable dependency for Ada's policy;
4. stdio read-only ReMe boundary works on the target Mac;
5. deterministic proposal validation passes the correction/conflict fixtures;
6. file truth remains authoritative after an out-of-band edit.

Until that bundle is reviewed, ADR-0008 remains Proposed.
