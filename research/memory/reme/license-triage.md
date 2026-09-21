# ReMe license and dependency triage for Ada

- **Status:** Preliminary source-verified triage
- **Date:** 2026-09-21
- **Purpose:** Identify obvious licensing blockers and the smallest plausible ReMe runtime path before an executable spike.

This is **not** a complete transitive dependency license audit.

## Proposed minimal characterization path

Do not use ReMe's `core` extra for the first Ada spike.

Current upstream packaging and source indicate that the realistic minimum for importing/using ReMe's AgentScope-backed Memory workflows is:

```text
reme-ai[as]
  -> ReMe
  -> AgentScope 2.0.7.post1 + model-ollama extra
  -> ollama Python client
```

## Source-verified top-level licenses

| Component | Version/path relevant to Ada | Verified top-level license | Ada status |
| --- | --- | --- | --- |
| ReMe | current 0.4.1.x source / `reme-ai` | Apache-2.0 | PASS |
| AgentScope | pinned by ReMe: `2.0.7.post1` | Apache-2.0 | PASS |
| Ollama Python client | `ollama>=0.5.4` through AgentScope extra | MIT | PASS |

These licenses are compatible with Ada's MIT distribution strategy, subject to normal notice/attribution obligations.

## Important dependency observation

AgentScope is not a small Ollama adapter.

At the pinned `2.0.7.post1` version its base package already depends on packages for, among other things:

- Anthropic;
- DashScope;
- OpenAI;
- MCP;
- OpenTelemetry API/SDK/exporter;
- Socket.IO;
- tree-sitter;
- PDF parsing;
- common HTTP/serialization/runtime utilities.

Adding `model-ollama` then adds the official Ollama client.

This does **not** mean Ada will call those providers. It does mean they are part of the installed dependency graph unless upstream packaging changes.

### Ada consequence

Even if licensing passes, adopting ReMe currently adds a second agent-framework dependency tree next to Ada's accepted PydanticAI runtime.

The decision gate should therefore consider:

- dependency count;
- supply-chain/security surface;
- startup/runtime footprint;
- duplicate model/provider abstractions;
- upgrade cadence and compatibility;
- whether Ada can isolate ReMe behind a narrow Memory process/adapter;
- whether a smaller extraction of ReMe's file/index concepts is cheaper long-term.

## Explicitly excluded from the minimal path

ReMe's current `core` extra additionally includes components such as:

- Claude Agent SDK;
- OpenAI Codex SDK;
- FAISS;
- zvec;
- Neo4j;
- NetworkX;
- Polars;
- ReMe Studio;
- proxy/image/search support.

These are **not required merely because ReMe offers them** and should not enter Ada's dependency/license review unless an Ada scenario justifies them.

This keeps the license review aligned with the actual selected runtime path.

## Full transitive audit still required

Before product adoption, generate an environment-specific dependency lock/SBOM for the exact chosen install and verify every runtime/build artifact.

The later executable spike should produce at least:

1. resolved package list and versions;
2. package license metadata;
3. source/project URL for each direct/transitive dependency where metadata is ambiguous;
4. binary/wheel provenance for architecture-specific packages;
5. dependency vulnerability scan;
6. NOTICE additions required by Apache-2.0 or bundled third-party notices.

Any package with:

- GPL/AGPL/SSPL/Elastic/non-commercial/custom terms;
- unclear/no license;
- downloaded binary/model with separate terms;

must stop automatic adoption until explicitly reviewed.

## Current conclusion

No top-level license blocker has been found on the **minimal ReMe + AgentScope + Ollama** path.

The larger concern is architectural/dependency footprint, not the verified licenses above.

Status:

```text
top-level license gate: PASS
minimal direct-path triage: PASS
full transitive license audit: OPEN
binary/model license audit: OPEN
```
