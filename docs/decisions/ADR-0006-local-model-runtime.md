# ADR-0006: Use self-hosted Ollama as the initial local model-serving baseline

- **Status:** Proposed
- **Date:** 2026-09-20

## Context

Ada's confirmed MVP requires local text chat. ADR-0002 already selected PydanticAI behind an Ada-owned runtime boundary and recorded a successful target-hardware prototype using Ollama with qwen3:8b and later qwen3.5:9b on the MacBook Air M1 / 16 GB baseline.

The remaining question is the first concrete local model-serving substrate. This decision should minimize new maintenance work while preserving:

- local/offline operation;
- macOS and Linux portability;
- replaceability behind AgentRuntimePort;
- compatibility with PydanticAI 2.46.0;
- modest setup and operational burden for a project maintained roughly 1–2 evenings per week;
- no requirement for a cloud account or external telemetry path.

The model itself is deliberately a separate, replaceable choice from the serving runtime.

## Candidates

### Ollama

- local HTTP model server with macOS and Linux support;
- MIT-licensed runtime;
- model pull/run lifecycle included;
- OpenAI-compatible API plus native PydanticAI 2.46.0 OllamaModel / OllamaProvider;
- already exercised on Ada's target M1 / 16 GB system with qwen3:8b;
- keeps model-process management outside Ada.

### llama.cpp server

- mature MIT-licensed low-level inference runtime;
- macOS/Linux support and strong Apple Silicon support;
- OpenAI-compatible server mode;
- gives more direct control, but Ada would own more model-file, launch/configuration, and operational glue.

### MLX-LM

- MIT-licensed and optimized for Apple Silicon;
- attractive target-Mac performance and Hugging Face integration;
- materially less aligned with Ada's desired Linux/vServer portability;
- would make the first local runtime more platform-specific than necessary.

## Decision matrix

Scores are 1–5 and represent Ada's current MVP needs rather than general product quality.

| Criterion | Weight | Ollama | llama.cpp server | MLX-LM |
| --- | ---: | ---: | ---: | ---: |
| Proven PydanticAI / target-hardware fit | 30% | 5 | 4 | 3 |
| Setup + maintainer burden | 25% | 5 | 3 | 4 |
| macOS + Linux portability | 20% | 5 | 5 | 2 |
| Local/offline privacy fit | 15% | 5 | 5 | 5 |
| Model lifecycle/distribution ergonomics | 10% | 5 | 3 | 4 |
| **Weighted score** |  | **5.00** | **3.90** | **3.35** |

## Decision

Use **self-hosted Ollama** as Ada's initial local model-serving baseline.

This means:

- Ada connects only to a loopback Ollama endpoint in the first local-chat profile;
- Ollama remains outside Ada's domain model and behind the PydanticAI runtime adapter;
- qwen3.5:9b is the current **target-hardware baseline model**, selected after a direct A/B test against qwen3:8b;
- the model name and endpoint are configuration, not hard architectural dependencies;
- cloud-hosted Ollama or arbitrary remote OpenAI-compatible endpoints are not part of this local profile.

The first runtime profile is:

- PydanticAI: 2.46.0
- Ollama endpoint: http://localhost:11434/v1
- model baseline: qwen3.5:9b
- Qwen-family reasoning disabled for ordinary chat using the model setting already validated in ADR-0002.

Current Ollama metadata lists qwen3.5:9b as a 9.65B-parameter Q4_K_M artifact at roughly 6.6 GB with Apache License 2.0. The earlier qwen3:8b (roughly 5.2 GB) remains a tested fallback. Model artifacts are downloaded by the user through Ollama and are not redistributed by Ada.

## Session history

The first CLI chat may keep conversation history **in memory for the lifetime of the process** so multi-turn conversation feels coherent.

That history:

- is runtime/session state only;
- is not authoritative Memory;
- is not persisted by Ada in this slice;
- is discarded when the process exits or the session is reset.

Persistent user-controlled Memory remains a separate later capability decision.

## Personality

The local-chat agent uses the product baseline in [Ada personality baseline](../product/personality.md).

Personality instructions are operator-authored model instructions. They are not a security boundary and must not grant authority, alter AdaGuard decisions, or turn conversation history into trusted facts.

## Consequences

### Positive

- fastest path from the existing foundation to a genuinely interactive local Ada;
- reuses a model/runtime combination proven on target hardware, with qwen3.5:9b selected after a direct qwen3:8b comparison;
- no new Python dependency is required because the existing PydanticAI OpenAI extra supports Ollama;
- simple Mac/Linux path;
- external model-process lifecycle stays out of Ada core.

### Negative

- users must install and run Ollama separately;
- Ollama becomes an MVP operational dependency even though it remains architecturally replaceable;
- OpenAI-compatible behavior is not identical across all models/providers and needs regression testing;
- the baseline qwen3.5:9b model remains replaceable and may be superseded after future quality/latency evaluation.

## Alternatives

### llama.cpp server

Keep as the primary fallback if Ollama adds unwanted behavior, lifecycle burden, or compatibility regressions. It remains attractive when Ada needs tighter control over inference and model files.

### MLX-LM

Keep as a possible Apple-specific optimized profile, but do not make it the initial baseline while Linux/vServer portability remains a project goal.

## Re-open triggers

Re-open this decision if:

- Ollama materially regresses local/offline behavior or PydanticAI compatibility;
- model serving becomes a significant memory/CPU/startup bottleneck;
- packaging requires embedding the model runtime instead of relying on an external local service;
- llama.cpp materially lowers lifetime operational cost;
- Linux/server deployment becomes incompatible with the chosen setup;
- a different model runtime provides clearly better privacy, lifecycle, or target-hardware performance without increasing maintenance burden.

## Validation required before acceptance

Before changing this ADR from Proposed to Accepted:

1. ada chat must complete a multi-turn local conversation on the target Mac.
2. The session must make no non-loopback model request.
3. The personality baseline must be observable without historical impersonation.
4. Existing local validation must remain green.


## Evidence references

- PydanticAI Ollama integration: https://ai.pydantic.dev/models/ollama/
- Ollama model metadata for qwen3.5:9b: https://ollama.com/library/qwen3.5:9b
- Earlier fallback metadata for qwen3:8b: https://ollama.com/library/qwen3:8b
- Ollama runtime: https://github.com/ollama/ollama
- llama.cpp: https://github.com/ggml-org/llama.cpp
- MLX-LM: https://github.com/ml-explore/mlx-lm


## First target-hardware validation

A first manual run on the target Mac confirmed:

- Ollama is available locally with both `qwen3:8b` and the earlier `ada-qwen3-8b-4k` profile;
- `ada chat` successfully produced a Lovelace-inspired modern self-description;
- `/reset` cleared the adapter's session context path.

The run also exposed issues that block acceptance:

1. PydanticAI printed its first-run observability banner into the product CLI.
2. The self-referential prompt "What did I just ask you?" did not reliably demonstrate prior-turn recall on qwen3:8b.
3. Most importantly, the model falsely answered "I've added..." to a calendar-create request even though this slice executed no action.

PR #22 now suppresses the framework banner and routes calendar-create requests through a typed, **non-executable `CreateCalendarEventDraft`** output path. Materially missing details stay unresolved instead of being invented to satisfy the executable proposal schema. Ada renders clarification deterministically and still executes nothing. Only a later application step may convert a complete draft into a `CreateCalendarEventProposal`.

ADR-0006 remains **Proposed** until the corrected path is re-tested.

For session-history validation, use an unambiguous semantic test rather than a self-referential question:

1. "For this session, remember the word cobalt."
2. "What word did I ask you to remember?"
3. `/reset`
4. "What word did I ask you to remember before the reset?"

The second answer should be "cobalt"; after reset Ada should state that the previous session context is unavailable rather than inventing an answer.


A second target-hardware run confirmed 41/41 automated tests and clean banner-free local chat. It also showed:

- explicit session recall worked before reset ("cobalt");
- after reset, qwen3:8b still hallucinated a word instead of admitting the prior context was unavailable;
- a partial German calendar request hit PydanticAI's output retry limit because the model was being asked to satisfy the strict executable proposal schema despite missing material details.

The branch now strengthens the standing personality instruction against invented session recall and separates `CreateCalendarEventDraft` from executable proposals. The draft schema permits missing fields, while Ada-owned deterministic code identifies required clarifications such as missing year or end time/duration.

ADR-0006 remains Proposed pending one more real-model re-test of those two corrected behaviors.


### Structured local-chat response transport

PydanticAI 2.46.0 documents that self-hosted Ollama v0.5.0+ enforces JSON Schema through its grammar-constrained decoder when `NativeOutput` is used. After target-hardware testing exposed retry failures on the default tool-output path, PR #22 switched the local chat response envelope to `NativeOutput([AgentTextReply, CreateCalendarEventDraft])`.

This keeps ordinary replies and calendar drafts type-safe without relying on output-tool calling. Calendar draft fields are all schema-required but nullable where information may legitimately be missing; the model must therefore explicitly represent missing information rather than omitting arbitrary fields.


## Model A/B validation

The target Mac was used to compare qwen3:8b with qwen3.5:9b using the same local-chat acceptance flow.

Observed maintainer feedback:

- qwen3.5:9b was not materially slower on the MacBook Air M1 / 16 GB target;
- German interaction felt more natural and coherent;
- post-reset uncertainty handling was better;
- the larger model still worked comfortably enough for the intended interactive development loop.

Based on that direct target-hardware evidence, qwen3.5:9b becomes the default local baseline while qwen3:8b remains a tested lower-footprint fallback.

This is a model-profile choice, not a new architecture dependency; the model remains configurable.
