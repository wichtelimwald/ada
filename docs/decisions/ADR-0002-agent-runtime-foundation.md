# ADR-0002: Use PydanticAI as the initial agent runtime foundation

- **Status:** Proposed
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

Use **PydanticAI as Ada's initial agent runtime foundation**.

PydanticAI is selected as runtime/orchestration infrastructure only. It does not become Ada's authority, memory owner, identity model or side-effect ledger.

The privileged action path must remain:

`model → typed proposal → Ada Guard → Ada action ledger → Ada provider adapter`

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

## Implementation constraints

1. Pin tested PydanticAI and Harness versions rather than tracking floating latest releases.
2. The prototype baseline is:
   - `pydantic-ai 2.46.0`
   - `pydantic-ai-harness 0.31.0`
3. Isolate Harness / StepPersistence behind an Ada-owned adapter because that surface is young and may change.
4. Keep observability and external telemetry disabled by default for the local profile.
5. Do not use framework approval/HITL as Ada's authorization boundary.
6. Do not use framework persistence as long-term authoritative user memory.
7. Give every consequential action a stable Ada operation ID before provider execution.
8. Treat provider commit with missing tool result as ambiguous until reconciled.
9. Explicitly configure and regression-test local model/provider behavior; do not assume unified model settings map correctly for every provider/model combination.
10. Do not add broad shell/browser/filesystem tools merely because the framework supports tools.
11. Multi-agent architecture is not required for the MVP; introduce additional agents only when a confirmed capability benefits from separation.

## Consequences

### Positive

- Small enough runtime surface to preserve clear Ada-owned boundaries.
- Strong typed-tool model for placing Ada Guard directly in the real side-effect path.
- Clean separation between runtime state and authoritative user memory.
- Local Ollama operation is viable on the target hardware.
- MCP/provider abstraction avoids building all model/tool plumbing from scratch.
- Multi-agent patterns remain possible later without forcing them into the MVP.

### Negative

- Ada must still build its own scheduler/background policy, mail/calendar/travel adapters, permission model, local UI and action ledger.
- Safe hard-crash recovery still requires Ada-owned reconciliation logic.
- Provider/model profile behavior can require explicit configuration and regression tests.
- Rapid upstream releases require disciplined version pinning and upgrade validation.
- Harness / StepPersistence is a younger dependency surface than the PydanticAI core.

## Alternatives considered

### OpenJarvis

Not selected as the initial foundation.

OpenJarvis demonstrated substantial reusable assistant infrastructure and passed the tested Ada Guard boundary without a fork. It remains the most important alternative.

It was not selected because Ada would inherit a larger dependency/audit surface, default external analytics that require hardening, broader capability surface than the MVP needs, and framework-level completion semantics that cannot be treated as authoritative action state.

Reconsider OpenJarvis if later evidence shows that its scheduler/server/local-assistant infrastructure materially lowers Ada's lifetime implementation and maintenance cost after unwanted memory, analytics and authority surfaces are constrained.

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
- maintaining the PydanticAI integration becomes comparable to maintaining a minimal Ada runtime.

## Follow-up

The next architecture work should define Ada-owned interfaces around the selected runtime rather than immediately building product features:

- `AdaGuard`
- `ActionLedger`
- privileged provider adapter contract
- runtime persistence adapter
- external authoritative memory boundary

The implementation should begin with the smallest vertical slice that preserves these boundaries.
