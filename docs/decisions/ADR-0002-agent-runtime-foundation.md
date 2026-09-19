# ADR-0002: Use PydanticAI behind a modular Ada runtime boundary

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

Ada needs an agent runtime that saves meaningful implementation work without owning or weakening Ada's core trust boundaries.

The confirmed MVP requires local text interaction, permissioned email/calendar actions, conflict detection, persistent user-controlled memory, recovery, logging, and explicit authority handling. Ada's architecture requires that:

- consequential side effects pass through an Ada-owned deterministic authorization boundary;
- authoritative long-term memory remains external to the agent runtime and directly user-controlled;
- runtime/tool/model output is never itself authority;
- side-effect success and retry safety remain Ada-owned;
- local/self-hosted operation works on the initial MacBook Air M1 / 16 GB target;
- external analytics or observability are not mandatory.

The following candidates were researched using agreed weights and hard gates:

- OpenJarvis
- PydanticAI
- Microsoft Agent Framework
- LangGraph
- minimal custom Ada runtime

OpenClaw was used as a feature/security benchmark only.

The final research matrix is documented in
[Agent runtime / foundation evaluation](../research/agent-runtime-foundation-evaluation.md).

Final weighted scores:

| Candidate | Score |
| --- | ---: |
| PydanticAI | **83** |
| Microsoft Agent Framework | 75 |
| OpenJarvis | 73 |
| LangGraph | 72 |
| Minimal Ada runtime | 62 |

No candidate was excluded by a hard gate.

## Evidence from targeted prototypes

### PydanticAI recovery

A prototype exercised:

`local model → typed action proposal → Ada Guard → Ada action ledger → fake calendar provider → crash → recovery`

Both an exception after provider commit and a hard `os._exit()` after provider commit recovered without a duplicate provider side effect.

The hard-exit case did not leave a continuable runtime snapshot. Safe recovery therefore depended on Ada-owned operation identity, action ledger and provider reconciliation.

Conclusion:

> PydanticAI persistence is useful runtime evidence and recovery support, but Ada remains the source of side-effect truth.

### OpenJarvis Guard boundary

One Ada-owned privileged fake calendar tool was exercised through direct ToolExecutor, MCP, a tool-using agent, scheduler execution and the canonical server/direct helper.

All tested paths reached the Ada Guard, and denied actions produced zero provider writes. No OpenJarvis fork was required.

However:

- agent/scheduler completion can still appear successful while a privileged tool was denied;
- external analytics are enabled by default in the tested configuration;
- OpenJarvis carries a substantially broader dependency and feature surface.

### Local model validation

Using the same local `qwen3:8b` model with a 4k context profile on the target M1 / 16 GB system:

- PydanticAI: 7.720 s mean / median;
- OpenJarvis: 8.619 s mean / 8.651 s median.

Both produced correct tool calls and outputs.

A framework-free comparison of Ollama's native and OpenAI-compatible APIs showed nearly identical latency, so the earlier slow PydanticAI runs were traced to Qwen3 reasoning configuration rather than a structural framework performance problem.

For the tested PydanticAI/Ollama/Qwen3 combination, explicit
`openai_reasoning_effort="none"` was required to obtain the intended non-reasoning behavior.

## Decision

Use **PydanticAI as Ada's initial agent-runtime implementation behind Ada-owned interfaces**.

The architectural decision is deliberately broader than "build Ada on PydanticAI":

> **Ada is the stable system; PydanticAI is the first replaceable runtime adapter.**

PydanticAI is selected as runtime/orchestration infrastructure only. It does not become Ada's authority, memory owner, identity model, side-effect ledger, application shell, or permanent architectural center.

The privileged action path must remain:

`model → typed proposal → Ada Guard → Ada action ledger → Ada provider adapter`

The Ada core must not require callers or domain code to depend directly on PydanticAI-specific types where an Ada-owned contract can express the requirement.

### Ada-owned responsibilities

Ada must own:

- permissions and authorization;
- person / data-subject / audience / authority semantics;
- long-term authoritative user memory;
- secrets handling;
- consequential-action state;
- stable operation IDs and idempotency;
- provider reconciliation after ambiguous failures;
- email/calendar/travel semantics;
- local privacy configuration and egress policy.

### PydanticAI responsibilities

PydanticAI may provide:

- model/provider abstraction;
- typed agent/tool execution;
- dependency injection;
- MCP integration;
- conversation/runtime glue;
- optional persistence/runtime evidence through StepPersistence/Harness.

### Modularity strategy

Ada should be designed as a small, stable core with explicit ports/interfaces around replaceable infrastructure.

Conceptually:

```text
Ada Core
├── Identity / Family / Audience
├── Permissions / Ada Guard
├── Action Ledger
├── Memory boundary
├── Scheduler port
├── Connector ports
├── Event / audit port
└── Agent-runtime port
       └── PydanticAI adapter (initial implementation)
```

The same principle applies outside the agent runtime:

- scheduler implementations must be replaceable behind an Ada-owned scheduler contract;
- mail, calendar, travel-time, and other integrations must sit behind narrow Ada-owned provider contracts;
- authoritative memory must remain behind an Ada-owned boundary and independent of runtime persistence;
- event/audit infrastructure must expose Ada semantics rather than third-party framework semantics;
- UI/server layers must communicate with Ada-owned application APIs rather than directly with PydanticAI.

This allows Ada to combine mature components without adopting another framework's complete architecture.

### Reuse and third-party components

Ada may reuse or adapt mature functionality from OpenJarvis or other projects when it reduces implementation and maintenance work.

Reuse should follow this preference order:

1. **Use a well-bounded dependency behind an Ada-owned interface** when a suitable component already exists.
2. **Adapt or wrap an isolated component** when direct use would leak third-party concepts into Ada core.
3. **Use an implementation as architectural inspiration** when its code or lifecycle model is not a good dependency fit.
4. **Implement Ada-specific functionality directly** when trust boundaries or semantics are unique to Ada.

OpenJarvis is therefore both:

- an important reference implementation for assistant plumbing such as scheduler, channels, connectors, server/UI, events, and proactive workflows; and
- a possible source of selectively reusable components where the dependency and license boundary remains clear.

The default is **not** to depend on OpenJarvis as Ada's global runtime.

### Licensing strategy

Ada-owned core code remains intended to use **MIT**.

When selecting reusable components:

- prefer MIT-compatible dependencies where functionality and quality are comparable;
- keep third-party code/dependencies isolated behind explicit interfaces where practical;
- do not relabel third-party code as MIT;
- preserve all applicable copyright, license, attribution, and NOTICE obligations;
- direct reuse of Apache-2.0 OpenJarvis code remains Apache-2.0-governed for that reused material even when used inside an MIT project;
- prefer a dependency/adapter boundary over copying substantial third-party implementation into the Ada core when that keeps licensing and upgrades cleaner.

The modularity goal is not "MIT at any cost"; it is to keep **Ada-owned architecture and code permissive, understandable, replaceable, and minimally coupled**.

## Implementation constraints

1. Depend on PydanticAI through an Ada-owned runtime adapter; domain/application code should not depend on PydanticAI-specific APIs unless unavoidable.
2. Pin tested PydanticAI and Harness versions rather than tracking floating latest releases.
3. The prototype baseline is:
   - `pydantic-ai 2.46.0`
   - `pydantic-ai-harness 0.31.0`
4. Isolate Harness / StepPersistence behind an Ada-owned adapter because that surface is young and may change.
5. Keep observability and external telemetry disabled by default for the local profile.
6. Do not use framework approval/HITL as Ada's authorization boundary.
7. Do not use framework persistence as long-term authoritative user memory.
8. Give every consequential action a stable Ada operation ID before provider execution.
9. Treat provider commit with missing tool result as ambiguous until reconciled.
10. Explicitly configure and regression-test local model/provider behavior; do not assume unified model settings map correctly for every provider/model combination.
11. Do not add broad shell/browser/filesystem tools merely because the framework supports tools.
12. Multi-agent architecture is not required for the MVP; introduce additional agents only when a confirmed capability benefits from separation.

## Consequences

### Positive

- Small enough runtime surface to preserve clear Ada-owned boundaries.
- Strong typed-tool model for placing Ada Guard directly in the real side-effect path.
- Clean separation between runtime state and authoritative user memory.
- Local Ollama operation is viable on the target hardware.
- MCP/provider abstraction avoids building all model/tool plumbing from scratch.
- Multi-agent patterns remain possible later without forcing them into the MVP.

### Negative

- Ada still owns the contracts and Ada-specific semantics for scheduler/background policy, mail/calendar/travel, permissions, UI/application APIs and the action ledger; some implementations may be reused from third-party components rather than built from scratch.
- Safe hard-crash recovery still requires Ada-owned reconciliation logic.
- Provider/model profile behavior can require explicit configuration and regression tests.
- Rapid upstream releases require disciplined version pinning and upgrade validation.
- Harness / StepPersistence is a younger dependency surface than the PydanticAI core.

## Alternatives considered

### OpenJarvis

Not selected as the initial foundation.

OpenJarvis demonstrated substantial reusable assistant infrastructure and passed the tested Ada Guard boundary without a fork. It remains the most important alternative and an important source of implementation ideas and potentially reusable isolated components.

It was not selected as the global runtime because Ada would inherit a larger dependency/audit surface, default external analytics that require hardening, broader capability surface than the MVP needs, and framework-level completion semantics that cannot be treated as authoritative action state.

This decision does **not** reject selective OpenJarvis reuse. Scheduler, connector, channel, server/UI, event, or proactive-workflow implementations may be evaluated independently and adopted behind Ada-owned interfaces when their reuse value exceeds their coupling, audit, upgrade, and licensing cost.

Reconsider OpenJarvis as the global runtime if later evidence shows that its integrated infrastructure materially lowers Ada's lifetime implementation and maintenance cost after unwanted memory, analytics and authority surfaces are constrained.

### Microsoft Agent Framework

Not selected initially.

MAF provides stronger workflow/checkpoint/HITL infrastructure than PydanticAI, but carries a larger and faster-moving runtime surface. Recent approval/middleware defects reinforce that Ada would still need its own Guard.

Reconsider if Ada's confirmed workflows require more durable orchestration than PydanticAI plus Ada-owned recovery can provide cleanly.

### LangGraph

Not selected initially.

LangGraph provides strong explicit graph, checkpoint and interrupt/resume semantics, but solves orchestration more than the surrounding personal-assistant platform. Ada would still build most MVP-specific infrastructure, and the prebuilt ToolNode is not Ada's security boundary.

Reconsider if explicit durable graph control becomes a primary requirement.

### Minimal custom Ada runtime

Not selected initially.

It offers maximum trust-boundary control but would require Ada to own provider normalization, MCP lifecycle, retries, cancellation, streaming, persistence, crash recovery, migrations and other runtime glue.

Keep it as a fallback/control if framework lifecycle cost approaches the cost of maintaining that infrastructure directly.

## Re-open triggers

Re-open this ADR if:

- PydanticAI can no longer support the Ada Guard boundary without patches;
- local/self-hosted support materially regresses;
- persistence/Harness churn causes sustained maintenance burden;
- Ada requires durable workflow semantics that are awkward or unsafe to implement around PydanticAI;
- OpenJarvis demonstrates materially lower lifetime cost after Ada-incompatible defaults/surfaces are removed;
- another candidate becomes materially better aligned with newly confirmed requirements;
- maintaining the PydanticAI integration becomes comparable to maintaining a minimal Ada runtime;
- Ada-owned interfaces fail to keep runtime/framework replacement reasonably bounded, indicating that the modularity strategy is not working in practice.

## Follow-up

The next architecture work should define the Ada-owned modular boundaries before substantial product implementation:

- `AdaGuard`
- `ActionLedger`
- privileged provider adapter contract
- runtime persistence adapter
- external authoritative memory boundary
- agent-runtime port with a PydanticAI adapter
- scheduler port
- connector/provider ports
- event/audit port
- Ada-owned application API for UI/server clients

The implementation should begin with the smallest vertical slice that preserves these boundaries.

For each missing MVP capability, evaluate **reuse / adapt / build** independently. OpenJarvis and other frameworks may supply implementations, but no individual component should become an implicit architectural owner merely because it was convenient to reuse.
