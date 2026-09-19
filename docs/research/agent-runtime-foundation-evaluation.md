# Technology evaluation — Agent runtime / foundation

**Status:** Research complete — weighted evaluation updated with targeted prototype evidence  
**Evidence:** [Agent Runtime / Foundation Deep Research](agent-runtime-foundation-deep-research.md)

## 1. Decision

Choose the smallest mature runtime/foundation that saves substantial Ada-compatible work without weakening Ada's privacy, memory, authority, or maintainability requirements.

This decision is deliberately above programming-language or UI-framework selection.

## 2. Hard gates

A hard-gate failure excludes a candidate regardless of weighted score.

- **H1 License/distribution:** no proprietary hosted service may be mandatory; Ada-owned code remains MIT-compatible.
- **H2 Local/self-hosted:** core path can run locally on the initial macOS/M1 system.
- **H3 Independent Ada Guard:** every consequential side effect can be forced through an Ada-owned deterministic authorization boundary.
- **H4 External authoritative memory:** no mandatory hidden long-term user memory inside the runtime.
- **H5 Narrow authority:** shell/browser/general filesystem access is not required for the MVP.
- **H6 Privacy:** no mandatory telemetry or external processing.

### Current hard-gate result

| Candidate | H1 | H2 | H3 | H4 | H5 | H6 | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenJarvis | Pass | Pass | Pass with Ada Guard hardening | Pass | Pass | Pass with privacy hardening | Continue |
| PydanticAI | Pass | Pass | Pass | Pass | Pass | Pass | Continue |
| Microsoft Agent Framework | Pass | Pass | Pass with Ada Guard hardening | Pass | Pass | Pass with privacy hardening | Continue |
| LangGraph | Pass | Pass | Pass with explicit Ada policy/action nodes | Pass | Pass | Pass | Continue |
| Minimal Ada runtime | Conditional on selected SDK/model licenses | Pass | Pass | Pass | Pass | Conditional on selected SDKs | Control option |

No candidate is currently excluded by a hard gate.

## 3. Agreed weights

Weights were agreed before scoring.

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

Multi-agent features, general browser/computer control, and raw plugin counts receive no bonus because they are not MVP requirements.

## 4. Scoring scale

- **5 — Excellent:** strong fit with little Ada-specific compensation.
- **4 — Good:** solid fit with bounded configuration/adaptation.
- **3 — Adequate:** usable, but meaningful Ada-specific work or risk remains.
- **2 — Weak:** significant mismatch, maintenance burden, or unused surface.
- **1 — Poor:** little useful reuse for this criterion.

Scores below are the final research scores used to support ADR-0002. Prototype evidence changed OpenJarvis' security-boundary score from 3 to 4; the later local-performance tests did not justify further score changes.

## 5. Weighted matrix

| Criterion | Weight | OpenJarvis | PydanticAI | Microsoft Agent Framework | LangGraph | Minimal Ada |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Useful MVP reuse | 25% | **5** | 3 | 4 | 2 | 1 |
| Security-boundary fit / Ada Guard | 20% | **4** | **5** | 4 | 4 | **5** |
| Maintainability & stability | 15% | 2 | **4** | 3 | **4** | 2 |
| Durability / recovery / side-effect safety | 15% | 3 | 4 | **4** | **4** | 2 |
| Local-first / privacy operating fit | 10% | 4 | **5** | 4 | **5** | **5** |
| Memory / data-model fit | 5% | 4 | **5** | 4 | 4 | **5** |
| Integration clarity | 5% | 3 | **5** | 4 | 4 | **5** |
| Complexity tax / unnecessary surface | 5% | 2 | 4 | 2 | 4 | **5** |
| **Weighted total / 100** | **100%** | **73** | **83** | **75** | **72** | **62** |

### Final research order

1. **PydanticAI — 83**
2. **Microsoft Agent Framework — 75**
3. **OpenJarvis — 73**
4. **LangGraph — 72**
5. **Minimal Ada runtime — 62**

The architectural selection is recorded separately in ADR-0002.

## 6. Score rationale

### OpenJarvis — 73

**Why reuse = 5:** only candidate already close to a local personal-assistant platform, with local engines, MCP, server, scheduler/event infrastructure and broader assistant plumbing.

**Why security = 4:** the #836 capability-gate failure was serious, but the targeted Ada prototype verified that an Ada-owned privileged tool remained the effective side-effect boundary across direct ToolExecutor, MCP, a tool-using agent, scheduler execution, and the canonical server/direct helper. Denied actions produced zero provider writes without a fork. It is not 5/5 because framework-level run success can still diverge from action success, auto-discovery must be constrained, and the historical enforcement defects justify continued defense in depth.

**Why maintenance = 2 / complexity = 2:** broad, young, fast-moving platform with the largest dependency/audit surface and substantial functionality Ada does not need in the MVP.

**Why local/privacy = 4:** strongest native local-engine story, but current external analytics require explicit disablement and egress regression testing.

### PydanticAI — 83

**Why security = 5:** typed application tools allow Ada Guard to sit naturally inside the actual side-effect adapter instead of depending on framework policy.

**Why memory = 5 / integration = 5:** application-owned conversation state, StepPersistence and long-lived memory are distinct. Ada can cleanly keep authoritative memory external.

**Why reuse = 3:** strong runtime glue, model providers, MCP and persistence primitives, but little ready-made personal-assistant platform.

**Why maintenance = 4:** active project with quick security response, but rapid release cadence requires strict pinning and upgrade tests. The local Qwen3 probe also showed that generic `thinking=False` did not disable reasoning for the tested Ollama profile; Ada must pin and regression-test provider-specific model settings such as `openai_reasoning_effort="none"`.

### Microsoft Agent Framework — 75

**Why reuse = 4 / durability = 4:** agent + workflow + checkpoint + HITL stack can remove more lifecycle code than a small agent SDK.

**Why security = 4:** Ada can retain its own side-effect boundary, but recent approval/middleware defects demonstrate that framework policy must remain defense in depth.

**Why maintenance = 3 / complexity = 2:** broad multi-provider platform, large surface and noticeable churn. Ada should use a narrow core slice only.

**Why local/privacy = 4:** local Ollama and file checkpoints are first-class; telemetry/instrumentation controls still need explicit hardening.

### LangGraph — 72

**Why durability = 4:** explicit graphs, checkpoints and interrupt/resume are strong.

**Why reuse = 2:** it solves orchestration more than personal-assistant infrastructure; Ada still owns most surrounding application capabilities.

**Why security = 4:** a clean Ada policy/action node works, but the prebuilt ToolNode should not be used as the security perimeter.

**Why local/privacy = 5:** framework core does not require remote model infrastructure or LangSmith.

### Minimal Ada runtime — 62

**Why security/memory/integration = 5:** Ada controls the trust boundary and data model completely.

**Why reuse = 1 / durability = 2 / maintenance = 2:** the apparent simplicity of the first prototype hides long-term work around provider changes, MCP lifecycle, retry/cancellation, persistence, crash recovery, idempotency and migrations.

The control confirms that using a framework is justified if it removes enough of this lifecycle work.

## 7. Prototype evidence

The targeted prototypes resolved the decision-critical uncertainties.

### PydanticAI recovery / side-effect safety

Prototype:

`local model → typed action proposal → Ada Guard → Ada action ledger → fake calendar provider → crash → recovery`

Results on the target Mac:

- exception after provider commit: safe recovery, exactly one provider side effect;
- hard `os._exit()` after provider commit: exactly one provider side effect;
- StepPersistence retained useful run/effect metadata, including the stable Ada operation id;
- a hard process death did not leave a continuable snapshot;
- safe recovery therefore came from Ada-owned operation identity, action ledger and provider reconciliation;
- no framework-internal patch or approval mechanism was used as the authority boundary.

Conclusion:

> PydanticAI provides useful runtime persistence and orchestration support, but Ada must own idempotency and consequential-action truth.

This supports durability = 4 rather than 5.

### OpenJarvis Guard boundary

One Ada-owned privileged fake calendar tool was exercised through:

- direct ToolExecutor,
- MCP `tools/call`,
- a real tool-using agent,
- scheduler execution,
- the canonical server/direct-operation helper.

Results:

- every tested path reached Ada Guard exactly once;
- denied actions produced zero provider writes;
- explicit MCP construction exposed only the supplied Ada tool;
- no OpenJarvis fork or source patch was required.

This raised Security-boundary fit from 3 to 4.

Important residual finding:

- agent/scheduler completion can still appear successful while an underlying privileged tool was denied.

Ada must therefore own explicit action state such as:

`proposed → denied | failed | committed`

and must never treat agent/scheduler completion as proof of a successful side effect.

### Local Ollama / Qwen3 performance

Target:

- MacBook Air M1 / 16 GB
- Ollama 0.33.2
- base model `qwen3:8b`
- 4k context alias
- one deterministic calendar-conflict tool
- temperature 0
- max 256 output tokens

Correctly configured results:

| Path | Mean | Median | Valid |
| --- | ---: | ---: | --- |
| PydanticAI | **7.720 s** | **7.720 s** | yes |
| OpenJarvis | **8.619 s** | **8.651 s** | yes |
| Direct Ollama native `/api/chat` | 10.717 s | 10.673 s | yes |
| Direct Ollama OpenAI-compatible `/v1/chat/completions` | 10.859 s | 10.938 s | yes |

The small timing differences are **not a framework-ranking criterion**. The conclusion is that both PydanticAI and OpenJarvis can provide acceptable local tool-calling performance on the target hardware when configured correctly.

A useful integration caveat was discovered:

- OpenJarvis' native Ollama engine disables Qwen3 thinking by default;
- PydanticAI 2.46.0 required the explicit provider-specific setting `openai_reasoning_effort="none"` in this test;
- generic `thinking=False` did not produce equivalent behavior for the tested local Qwen3 profile.

Ada must therefore pin and regression-test local model/provider settings.

### Ollama API-path isolation

A framework-free comparison showed:

- native `/api/chat`: 10.717 s mean;
- OpenAI-compatible `/v1/chat/completions`: 10.859 s mean.

The API-path difference was only about 1.3%, so it did not explain the earlier slow PydanticAI runs.

## 8. Residual risks

### PydanticAI

- StepPersistence / Harness is still a young surface and must be isolated behind an Ada adapter.
- Hard process death still requires Ada-owned reconciliation semantics.
- Provider/model profiles can have behavior gaps; local model settings require explicit regression tests.
- PydanticAI does not supply Ada's scheduler, mail/calendar integration, local UI, identity/audience model or permission system.

### OpenJarvis

- external analytics are enabled by default in the tested configuration and must be disabled and egress-tested;
- broad dependency and feature surface increases audit and upgrade cost;
- automatic tool discovery is inappropriate for Ada's privileged runtime profile; explicit allowlists are required;
- framework-level completion is not authoritative action status;
- large amounts of platform capability are outside Ada's MVP and remain maintenance surface even if unused.

### Microsoft Agent Framework and LangGraph

Both remain credible alternatives but no unresolved evidence currently justifies displacing the higher-scoring PydanticAI option.

## 9. Research conclusion

The weighted matrix and prototype evidence support **PydanticAI as Ada's initial agent runtime foundation**.

The reason is not that it has the most features. It provides the best current balance of:

- clean Ada-owned security boundary,
- external authoritative memory,
- typed tools and MCP,
- local model support,
- useful persistence/runtime primitives,
- low enough framework surface to audit and maintain.

OpenJarvis remains the most important alternative because it offers substantially more ready-made personal-assistant infrastructure. The Guard prototype showed that Ada could retain its own authority boundary without forking it. Its lower score is driven primarily by lifecycle/audit/privacy/complexity cost rather than inability to satisfy Ada's architecture.

The minimal custom runtime remains a control/fallback rather than the preferred path.

## 10. Decision constraints carried into ADR-0002

Selecting PydanticAI does **not** delegate the following to PydanticAI:

- authorization or permission decisions;
- long-term authoritative Ada Memory;
- identity, audience or guardian semantics;
- side-effect truth / exactly-once guarantees;
- mail/calendar/travel provider semantics;
- secrets management.

Required boundary:

`model → typed proposal → Ada Guard → Ada action ledger → Ada provider adapter`

Required implementation rules:

- pin tested PydanticAI / Harness versions;
- isolate Harness/StepPersistence behind an Ada-owned adapter;
- use explicit local model/provider settings and regression tests;
- keep observability/telemetry off by default in the local profile;
- keep authoritative user memory outside the runtime;
- give every consequential action a stable Ada operation id;
- reconcile ambiguous provider outcomes before retrying.

## 11. Re-open triggers

Re-open the runtime decision if any of the following becomes true:

- PydanticAI can no longer support the Ada Guard boundary without framework patches;
- local/self-hosted operation materially regresses;
- Harness/persistence churn creates sustained upgrade burden;
- Ada's workflows require durable graph semantics that the current approach cannot provide cleanly;
- OpenJarvis demonstrates materially lower lifetime implementation and maintenance burden after unwanted memory, analytics and broad authority surfaces are removed;
- MAF or LangGraph gains a clearly superior fit for newly confirmed MVP requirements;
- a minimal Ada runtime becomes simpler to maintain than the selected framework integration.

## 12. ADR gate

The research gate is satisfied:

- hard gates evaluated;
- weights agreed before scoring;
- weighted matrix completed;
- PydanticAI recovery prototype completed;
- OpenJarvis Guard-boundary prototype completed;
- local model behavior validated on the target M1/16 GB system;
- provider/API performance anomaly isolated.

ADR-0002 may now record the runtime selection.
