# Agent Runtime / Foundation Deep Research

**Date checked:** 2026-09-19  
**Status:** Research evidence; not an architecture decision.

## Executive finding

None of the evaluated frameworks should own Ada's authority, authoritative long-term memory, or side-effect guarantee.

For all candidates, the robust Ada architecture remains:

`LLM proposal → deterministic Ada Guard → Ada-owned side-effect adapter → external system`

Framework HITL, tool approval, capability policies, middleware, and checkpoints may add defense in depth or workflow convenience, but they are not Ada's root of trust.

Under that condition, all four main candidates can satisfy Ada's current hard gates. The main difference is how much useful infrastructure Ada can reuse versus how much dependency, audit, upgrade, and attack surface the framework introduces.

## Executive comparison

| Candidate | Hard gates | Strongest Ada value | Main concern | Ada-specific work |
| --- | --- | --- | --- | --- |
| **OpenJarvis** | Pass with explicit hardening for Guard/privacy | Broadest personal-assistant foundation: local engines, tools/MCP, server, scheduler, event/audit infrastructure | Young and broad codebase; capability enforcement had a serious P0 failure; external analytics are not privacy-first by default | Medium if Ada replaces critical authority/memory boundaries rather than trusting framework defaults |
| **PydanticAI** | Clean pass | Typed agent loop, tools, MCP, provider abstraction, local models, clean separation of application state | Limited personal-assistant platform functionality; Ada still owns scheduler, integrations, host/UI and much of recovery | Medium to high |
| **Microsoft Agent Framework** | Pass with hardening | Agent/workflow runtime, MCP, checkpoints, HITL, Ollama support | API churn, broad platform surface, recent approval/middleware security defects, privacy settings require explicit hardening | Medium |
| **LangGraph** | Pass if Guard is explicit and outside ToolNode internals | Strong explicit state machine, checkpointing, interrupt/resume and recovery primitives | Limited assistant platform, no stable first-class pre-tool policy hook, resume is not exactly-once for side effects | Medium to high |
| **Minimal Ada runtime** | Pass by design, depending on chosen SDKs/models | Smallest trust boundary and maximum control | Ada must own orchestration, recovery, provider/MCP lifecycle, scheduling, retries, logging and migrations | Very high |

## Hard gates

Legend: **Pass** means the requirement can be met without proprietary mandatory infrastructure. **Pass with hardening** means Ada can meet it, but framework defaults or convenience paths must not be accepted as-is.

| Gate | OpenJarvis | PydanticAI | Microsoft Agent Framework | LangGraph | Minimal Ada |
| --- | --- | --- | --- | --- | --- |
| H1 License / distribution | Pass — Apache-2.0 | Pass — MIT | Pass — MIT | Pass — MIT core | Depends on selected SDKs/models |
| H2 Local / self-hosted | Pass — Ollama, llama.cpp, MLX paths | Pass — Ollama / OpenAI-compatible local APIs | Pass — official Ollama client; local checkpoints | Pass — model-agnostic runtime | Pass by design |
| H3 Independent Ada Guard | Pass with hardening | Strong fit | Pass with hardening | Pass with explicit Ada policy/tool node | Pass by design |
| H4 External editable authoritative memory | Pass — internal memory can be disabled/replaced | Strong fit | Pass — avoid/replace higher-level memory features | Pass — keep checkpoints separate from Ada Memory | Pass |
| H5 No mandatory broad host authority | Pass | Pass | Pass for core | Pass | Pass |
| H6 Privacy / no mandatory egress | Pass with hardening — external analytics currently need explicit disablement | Pass — observability optional | Pass with hardening — instrumentation/UA/feature telemetry must be controlled | Pass — LangSmith optional | Depends on selected SDKs |

### H1 — Licensing

OpenJarvis is Apache-2.0. Ada-owned code can remain MIT, subject to Apache notice/attribution obligations and the licenses of transitive dependencies and model assets.

PydanticAI, Microsoft Agent Framework and LangGraph core are MIT.

For all candidates, framework license is not sufficient evidence for model, voice, dataset, asset or optional provider licensing. A concrete Ada distribution will still require dependency/model license review and an SBOM.

### H2 — Local operation

OpenJarvis has the broadest native local-engine coverage and explicit Apple-Silicon support, including Ollama, llama.cpp-compatible paths and MLX-oriented operation.

PydanticAI officially supports local Ollama endpoints and OpenAI-compatible local endpoints.

Microsoft Agent Framework is not Azure-dependent. It has an official `OllamaChatClient` path and supports local file checkpointing.

LangGraph is model-agnostic; local inference can be implemented through any suitable client inside graph nodes.

For all candidates, practical M1/16 GB quality is more likely to be constrained by the chosen local model and tool-calling quality than by the framework runtime itself.

### H3 — Independent Ada Guard

Framework approval must never be treated as authorization.

OpenJarvis issue #836 documented four independent defects that made capability enforcement effectively non-functional on several paths. PR #827 substantially rewired capability/rate-limit/audit enforcement across server, managed-agent, CLI/SDK, MCP, scheduler and learning paths and added fail-closed tests.

This supports the interpretation that OpenJarvis had an immature enforcement implementation around a usable capability architecture rather than proving the architecture itself impossible. It also demonstrates why Ada must not make framework capability enforcement its root of trust.

PydanticAI fits Ada's model cleanly because privileged tools can remain ordinary typed application functions whose first effective side-effect step calls Ada Guard.

Microsoft Agent Framework had a recent approval bypass affecting some batched tool calls, and middleware fail-closed behavior also required upstream work. Therefore MAF approval/middleware cannot be Ada's authority boundary.

LangGraph does not currently offer a stable first-class pre-tool policy hook around its prebuilt `ToolNode`. Ada should not patch private internals. Use an explicit Ada policy node or put the Guard directly in every privileged Ada tool/action executor.

### H4 — Memory

Ada's authoritative personal memory must remain outside the framework runtime.

OpenJarvis fact memory is optional and can be disabled/replaced. Its built-in memory should not become Ada's source of truth.

PydanticAI separates application-owned conversation history, `StepPersistence`, optional long-term `Memory`, and durable execution concepts particularly cleanly. This maps well to Ada's requirement:

`Ada Memory ≠ conversation history ≠ execution checkpoint ≠ action ledger`

Microsoft Agent Framework supports local checkpoint backends. Higher-level harness memory/file features should be avoided or explicitly constrained for Ada.

LangGraph checkpoints are useful workflow state, not authoritative user memory. Ada Memory should remain a separate store.

### H5 — Host authority

None of the four candidates requires shell, browser automation, or unrestricted filesystem access for Ada's MVP.

Ada should register only narrow capabilities such as:

- read/write Ada Memory through scoped APIs,
- read/draft/send mail through Ada adapters,
- read/create/update calendar events through Ada adapters,
- calculate travel time through a narrow service,
- a small set of administrative operations.

Generic shell, browser automation, code execution and general filesystem tools should not be registered in the MVP.

### H6 — Privacy / telemetry

OpenJarvis currently requires an explicit privacy baseline because external anonymous analytics are enabled by default in current configuration. Ada would need to disable them and regression-test egress.

PydanticAI observability is optional. Web-fetch and tracing capabilities still need version pinning and conservative configuration because recent security fixes affected those areas.

Microsoft Agent Framework supports local operation, but instrumentation/user-agent/feature telemetry controls need to be explicitly hardened and tested.

LangGraph core does not require LangSmith.

## Candidate assessments

### OpenJarvis

OpenJarvis is the only candidate that already resembles a personal-assistant platform rather than primarily an agent SDK/runtime.

Potential reusable value includes:

- local inference engine abstractions,
- Apple-Silicon-oriented local model support,
- agent/runtime infrastructure,
- MCP,
- server/desktop infrastructure,
- scheduler/event infrastructure,
- audit/security infrastructure,
- optional channels and tools.

The P0 capability-gate failure was serious. It involved multiple independent defects and multiple unguarded execution paths. The merged fix is also substantial and broad, which argues against dismissing OpenJarvis outright.

**Ada interpretation:** use OpenJarvis policy only as defense in depth. Keep actual authorization in Ada-owned side-effect adapters.

**Potentially reusable unchanged/configured:** local engine layer, MCP base, scheduler/event infrastructure, parts of server/UI, safe tool plumbing.

**Ada adapters required:** `AdaGuard`, `AdaMemory`, identity/person/audience context, mail/calendar/travel adapters.

**Replace/avoid:** built-in fact memory as authoritative memory; framework policy as sole authorization.

**Current risk:** highest audit and dependency surface of the candidates; privacy defaults require hardening; project metadata still reflects a young/fast-moving platform.

**Fork requirement:** no mandatory fork is currently proven, provided Ada targets a version/revision containing the #827 capability fix.

### PydanticAI

PydanticAI is a typed agent SDK rather than a full assistant platform.

Strong reusable areas:

- agent loop,
- typed function tools,
- structured outputs,
- dependency injection,
- MCP,
- local/remote model provider abstraction,
- Ollama,
- deferred tools/HITL,
- `StepPersistence` and related execution state mechanisms.

The storage model is unusually compatible with Ada. Conversation storage, step persistence, long-lived model-written memory, and durable execution are distinct concepts.

**Potentially reusable unchanged/configured:** agent loop, typed tools, MCP, model providers, possibly deferred tools/HITL and StepPersistence.

**Ada adapters required:** Guard, authoritative Memory, identity/audience context, mail/calendar/travel, local host/UI.

**Ada-specific work remains:** scheduler, family/shared-scope model, authority grants, action/recovery service and application shell.

**Avoid:** framework/model-written long-term memory as Ada truth; approval as authorization; unnecessary web/tracing capabilities.

**Maintenance:** very active development and quick security response, but upgrade discipline and version pinning are essential.

### Microsoft Agent Framework

MAF is broader than PydanticAI and provides more workflow lifecycle infrastructure.

Useful areas:

- core agents,
- function tools,
- MCP,
- local Ollama support,
- workflow orchestration,
- checkpoints,
- HITL,
- middleware,
- observability hooks.

Local operation is a first-class supported scenario. Azure is not required for Ada core operation.

**Potentially reusable unchanged/configured:** core agent runtime, function tools, MCP, Ollama, workflow/checkpoint/HITL.

**Ada adapters required:** Guard at the effective side-effect boundary, authoritative Memory, identity/audience context, mail/calendar/travel.

**Avoid:** framework approval/middleware as authorization; broad higher-level harness capabilities; unwanted instrumentation/telemetry.

**Maintenance risk:** large and fast-moving multi-provider platform with more API churn and more surface than Ada needs. A narrow MAF slice is materially more attractive than adopting the full stack.

### LangGraph

LangGraph is a low-level durable graph/state runtime.

Its main Ada value is explicit workflow state and pause/resume.

A key documented semantic is that interrupted or retried nodes can execute again from the beginning. Therefore checkpointing is not an exactly-once guarantee for mail/calendar effects.

Ada would still need an idempotent action ledger, for example:

`planned → authorized → executing → committed / failed`

with stable operation IDs and provider IDs.

**Potentially reusable unchanged/configured:** graph runtime, checkpointing, interrupts/resume, conditional routing, saver implementations.

**Ada adapters required:** model/tool integration, Guard, Memory, mail/calendar/travel, scheduler and UI.

**Avoid:** ToolNode internals as the security boundary; graph checkpoint state as authority; checkpoints as the action ledger.

LangGraph is strongest if durable explicit workflows are valued more than ready-made assistant functionality.

### Minimal Ada runtime

A minimal custom runtime could start small:

- model client,
- model → tool proposal → result loop,
- typed tool schemas,
- MCP client,
- Ada Guard,
- Ada Memory,
- SQLite action ledger,
- small scheduler.

This provides the clearest trust boundary but creates long-term maintenance obligations for:

- provider changes,
- streaming,
- tool-call normalization,
- retries/cancellation,
- MCP lifecycle,
- malformed calls,
- history serialization,
- crash recovery,
- idempotency,
- migrations,
- observability,
- concurrency,
- resume semantics.

It remains the control option: a framework is justified only if the reusable Ada-compatible infrastructure saves more effort than its integration, audit and upgrade cost.

## Decision criteria

The hard gates are pass/fail and must not be compensated through scoring.

The maintainer agreed the following weights for the weighted evaluation:

| Criterion | Weight |
| --- | ---: |
| Useful MVP reuse | 25% |
| Security-boundary fit / Ada Guard | 20% |
| Maintainability & stability | 15% |
| Durability / recovery / side-effect safety | 15% |
| Local-first / privacy operating fit | 10% |
| Memory / data-model fit | 5% |
| Integration clarity | 5% |
| Complexity tax / unnecessary surface | 5% |
| **Total** | **100%** |

Multi-agent orchestration and general computer/browser control receive no bonus because they are not MVP requirements.

## Prototype questions

Only prototype uncertainties that could change the decision.

### OpenJarvis

Register one Ada-owned privileged action adapter and attempt to reach it through every Ada-relevant execution path:

- normal agent loop,
- scheduler/background path,
- MCP path,
- server/API path.

The purpose is not to re-test #836. It is to prove that the Ada-owned Guard boundary cannot be bypassed by framework dispatch paths.

### PydanticAI

Crash-test `StepPersistence` / tool-effect behavior around an external side effect:

1. authorize an Ada action,
2. execute the external side effect,
3. kill the process before the framework receives the tool result,
4. restart,
5. verify a thin Ada adapter can avoid duplicate execution and reconstruct the committed result.

### Microsoft Agent Framework

On the real M1/16 GB target:

- Ollama,
- multiple/batched tool calls,
- MCP,
- local file checkpoint/resume,
- Ada action envelopes.

Verify that Ada Guard receives the same stable authorized action identity across batching and resume.

### LangGraph

Crash-test an Ada action ledger around repeated node execution and verify duplicate send/create operations are suppressed at every tested crash point.

### Shared local-model test

Use the same local model class and the same narrow mail/calendar tool schemas across candidates. Measure:

- correct tool selection,
- argument validity,
- latency,
- memory use.

This is evidence about practical local MVP quality, not a framework-specific bonus.

## Preliminary shortlist

**Continue to weighted evaluation:**

- OpenJarvis — highest possible platform reuse; explicit security/privacy risk marker.
- PydanticAI — cleanest application/runtime separation; potentially more Ada-owned foundation work.
- Microsoft Agent Framework — strong workflow/runtime reuse; narrow usage and hardening required.
- LangGraph — strong durable workflow primitives; less assistant infrastructure.

**Benchmark/fallback:**

- Minimal Ada runtime — control for framework complexity.
- OpenClaw — feature benchmark only, not a scored foundation candidate.

No main candidate currently fails a hard gate.

## ADR-ready conclusions

1. Ada Guard must remain framework-independent and execute at the real side-effect boundary.
2. Framework approval/policy is defense in depth, never authority.
3. Ada Memory must remain authoritative and external to the runtime.
4. Runtime persistence/checkpoints and action ledgers are separate from user memory.
5. OpenJarvis has the highest reuse upside and the largest audit/dependency surface.
6. PydanticAI has the cleanest fit with Ada-owned Guard/Memory but leaves more platform work to Ada.
7. MAF is genuinely local-capable and does not require Azure, but should be adopted only as a narrow slice if chosen.
8. LangGraph is strongest as durable orchestration, not as a personal-assistant platform.
9. Minimal custom remains the control: a framework must save more lifetime work than it creates.
10. The next decision step is a weighted evidence matrix followed by only the prototypes that can materially change the ranking.

## Primary research references

- OpenJarvis capability-gate issue #836: https://github.com/open-jarvis/OpenJarvis/issues/836
- OpenJarvis capability enforcement fix #827 / commit `da30b30`: https://github.com/open-jarvis/OpenJarvis/pull/827
- OpenJarvis repository: https://github.com/open-jarvis/OpenJarvis
- PydanticAI repository: https://github.com/pydantic/pydantic-ai
- PydanticAI message history / StepPersistence: https://github.com/pydantic/pydantic-ai/blob/main/docs/message-history.md
- Microsoft Agent Framework repository: https://github.com/microsoft/agent-framework
- Microsoft Agent Framework checkpoint documentation: https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints
- LangGraph repository: https://github.com/langchain-ai/langgraph
- LangGraph interrupt semantics: https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/types.py
