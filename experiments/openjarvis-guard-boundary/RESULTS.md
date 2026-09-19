# Results — OpenJarvis Guard-boundary experiment

**Status:** Executed successfully on the target MacBook Air M1 / 16 GB.

## Environment

- OpenJarvis revision: `b03203fb91e3c9a2a23815eb50d5e93b4c0ba4cc`
- OpenJarvis package: `1.0.5.dev5+gb03203f`
- Python: 3.13.15
- macOS / Apple M1 / 16 GB
- analytics default reported by config: **enabled**
- install resolved 65 packages and installed 61 packages

The shell had an unrelated pre-existing `VIRTUAL_ENV` pointing at another project. `uv` correctly ignored it and created the experiment-local `.venv`.

## Paths

| Path | Allowed guard checks | Allowed writes | Denied guard checks | Denied writes | Pass |
| --- | ---: | ---: | ---: | ---: | --- |
| ToolExecutor | 1 | 1 | 1 | 0 | yes |
| MCP tools/call | 1 | 1 | 1 | 0 | yes |
| Tool-using agent | 1 | 1 | 1 | 0 | yes |
| Scheduler | 1 | 1 | 1 | 0 | yes |
| Server/direct helper | 1 | 1 | 1 | 0 | yes |

Overall probe result: **all_passed = true**.

## Main finding

For the tested OpenJarvis paths, an Ada-owned privileged tool can keep the real deterministic authorization boundary inside its own `execute()` implementation.

The following invocation paths all reached the same Ada Guard before provider mutation:

- direct `ToolExecutor`
- MCP `tools/call`
- a real OpenJarvis tool-using agent
- scheduler execution
- the canonical server/direct-operation helper

When the Guard denied the action, provider writes stayed at zero in every case.

This materially reduces the earlier concern that OpenJarvis would require a fork merely to enforce Ada's own side-effect boundary.

## Important caveat: framework success is not action truth

The denied agent and scheduler cases still reported their overall framework execution as successful while the tool result itself contained:

`Tool execution error: Ada Guard denied calendar.create`

That means Ada must not derive "action succeeded" from:

- agent-run completion,
- scheduler-run completion,
- or a generated final answer.

Ada still needs its own action/result contract and action ledger to distinguish:

- proposed
- denied
- failed
- committed

This is consistent with the PydanticAI experiment: the framework may orchestrate work, but Ada owns consequential-action truth.

## MCP exposure

When the MCP server was explicitly constructed with only the Ada calendar tool, `tools/list` exposed only:

`ada_calendar_create`

No unexpected built-in tools were exposed in this configuration.

This does not prove that OpenJarvis auto-discovery is safe for Ada. Ada should use explicit allowlisted tool construction, not automatic discovery, for privileged runtime profiles.

## Privacy finding

`AnalyticsConfig().enabled` returned **true**.

Current OpenJarvis also installs `posthog` as a core dependency in the tested environment.

For Ada this means:

- external analytics must be explicitly disabled in the Ada profile;
- egress regression tests are required;
- the default OpenJarvis privacy posture is not acceptable unchanged for Ada.

## Dependency / maintenance observation

The experiment installation resolved 65 packages and installed 61 packages before optional inference/server extras.

This confirms OpenJarvis' larger dependency and audit surface relative to a smaller SDK such as PydanticAI.

That cost must be weighed against its much broader reusable assistant infrastructure.

## Fork / patch requirement

**No fork or OpenJarvis source patch was required for this Guard-boundary experiment.**

The experiment used public OpenJarvis extension points:

- `BaseTool`
- `ToolExecutor`
- MCP server with explicit tools
- tool-using agent construction
- scheduler/system adapter
- `execute_secured_tool`

Ada-specific authorization remained entirely inside Ada-owned code.

## First local Ollama smoke attempt

The first `qwen3:8b` smoke attempt destabilized the target Mac before producing a result.

Post-analysis found that OpenJarvis' Ollama engine defaults to `num_ctx=16384` when `JARVIS_NUM_CTX` is unset. That made the initial comparison unnecessarily aggressive on the M1/16 GB target and asymmetric with the PydanticAI probe.

This incident is therefore recorded as a **test-design issue, not yet an OpenJarvis framework failure**.

The smoke probe has been changed to:

- `JARVIS_NUM_CTX=4096`
- `max_tokens=256`
- `max_turns=3`

Do not use the failed first attempt for scoring until the capped-context rerun is available.

## Local Ollama smoke test — capped context

Rerun after correcting the first probe to `JARVIS_NUM_CTX=4096`:

- model: `qwen3:8b`
- context: 4096
- output tokens cap: 256
- result: **success**
- tool selected: `calendar_conflicts`
- tool result: correct
- turns: **2**
- end-to-end latency: **34.612 s**
- final answer: correctly identified the 15:00 / 15:15 conflict and 25-minute travel-time issue
- system stability: stable

This confirms OpenJarvis can run the Ada-style local tool-calling slice on the target M1/16 GB system when the context is constrained appropriately.

The earlier 16k-context crash remains recorded as a test-design/configuration issue rather than a framework failure.

## Decision impact

### Security-boundary fit / Ada Guard

**Increase from 3/5 to 4/5.**

Reason:

- all tested relevant execution paths respected the Ada-owned tool boundary;
- denied actions produced zero provider writes;
- no fork or framework-internal patch was required.

Why not 5/5:

- the experiment covers representative paths, not every OpenJarvis execution surface;
- OpenJarvis has a history of capability-enforcement defects;
- framework-level run success can diverge from actual privileged-action success;
- Ada still must constrain tool exposure explicitly.

### Useful MVP reuse

**Remains 5/5.**

The experiment reinforces that scheduler, MCP, agent runtime and server/tool plumbing can be reused while retaining an Ada-owned Guard.

### Local-first / privacy operating fit

**Remains 4/5.**

Local operation is strong, but external analytics are enabled by default and require explicit hardening.

### Maintainability & stability

**Remains 2/5.**

The large dependency surface and young/fast-moving codebase remain material.

### Complexity tax

**Remains 2/5.**

The platform contains considerably more functionality than Ada's first MVP needs.

## Provisional weighted impact

Changing only Security-boundary fit from 3 → 4 changes OpenJarvis' provisional weighted score from **69 → 73**.

This does not make OpenJarvis the current leader, but it materially narrows the gap:

1. PydanticAI — 83
2. Microsoft Agent Framework — 75
3. **OpenJarvis — 73**
4. LangGraph — 72
5. Minimal Ada runtime — 62

The result justifies keeping OpenJarvis in the serious shortlist rather than treating it mainly as a benchmark.

## ADR implication

OpenJarvis no longer appears to require rebuilding or forking its critical tool-dispatch core merely to preserve Ada Guard.

The remaining decision is therefore a real trade-off:

- **PydanticAI:** cleaner, smaller, stronger separation; more Ada application infrastructure to build.
- **OpenJarvis:** much more reusable assistant infrastructure; larger dependency/privacy/audit surface and more behavior that Ada must constrain.

Before the final ADR, the most valuable remaining comparison is no longer another Guard test. It is a **reuse/dependency slice**: determine how much of OpenJarvis' scheduler, server/local chat, model runtime, and connector infrastructure Ada can actually adopt without also adopting unwanted memory, analytics, broad tools, or authority semantics.
