# Technology evaluation — Agent runtime / foundation

**Status:** Research — provisional weighted evaluation before targeted prototypes  
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

Scores below are intentionally provisional. Only evidence-backed uncertainties that could change the ranking should be prototyped.

## 5. Weighted matrix

| Criterion | Weight | OpenJarvis | PydanticAI | Microsoft Agent Framework | LangGraph | Minimal Ada |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Useful MVP reuse | 25% | **5** | 3 | 4 | 2 | 1 |
| Security-boundary fit / Ada Guard | 20% | 3 | **5** | 4 | 4 | **5** |
| Maintainability & stability | 15% | 2 | **4** | 3 | **4** | 2 |
| Durability / recovery / side-effect safety | 15% | 3 | 4 | **4** | **4** | 2 |
| Local-first / privacy operating fit | 10% | 4 | **5** | 4 | **5** | **5** |
| Memory / data-model fit | 5% | 4 | **5** | 4 | 4 | **5** |
| Integration clarity | 5% | 3 | **5** | 4 | 4 | **5** |
| Complexity tax / unnecessary surface | 5% | 2 | 4 | 2 | 4 | **5** |
| **Weighted total / 100** | **100%** | **69** | **83** | **75** | **72** | **62** |

### Provisional order

1. **PydanticAI — 83**
2. **Microsoft Agent Framework — 75**
3. **LangGraph — 72**
4. **OpenJarvis — 69**
5. **Minimal Ada runtime — 62**

This is **not** the ADR decision.

## 6. Score rationale

### OpenJarvis — 69

**Why reuse = 5:** only candidate already close to a local personal-assistant platform, with local engines, MCP, server, scheduler/event infrastructure and broader assistant plumbing.

**Why security = 3:** the #836 capability-gate failure was serious and affected multiple execution paths. The broad fix keeps OpenJarvis viable, but Ada must maintain an independent side-effect boundary.

**Why maintenance = 2 / complexity = 2:** broad, young, fast-moving platform with the largest dependency/audit surface and substantial functionality Ada does not need in the MVP.

**Why local/privacy = 4:** strongest native local-engine story, but current external analytics require explicit disablement and egress regression testing.

### PydanticAI — 83

**Why security = 5:** typed application tools allow Ada Guard to sit naturally inside the actual side-effect adapter instead of depending on framework policy.

**Why memory = 5 / integration = 5:** application-owned conversation state, StepPersistence and long-lived memory are distinct. Ada can cleanly keep authoritative memory external.

**Why reuse = 3:** strong runtime glue, model providers, MCP and persistence primitives, but little ready-made personal-assistant platform.

**Why maintenance = 4:** active project with quick security response, but rapid release cadence requires strict pinning and upgrade tests.

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

## 7. Sensitivity / uncertainty

The matrix has one clear provisional leader, but two uncertainties could materially change the decision:

### PydanticAI uncertainty

If `StepPersistence` plus a thin Ada action layer handles crash/restart/idempotency well in practice, its reuse/durability value is stronger than the current conservative score.

If not, Ada must build more lifecycle infrastructure and its lead narrows.

### OpenJarvis uncertainty

OpenJarvis scores poorly because its large reuse upside is offset by security, maintenance and complexity risk.

A small prototype can determine whether an Ada-owned Guard can remain a single non-bypassable boundary across the relevant OpenJarvis execution paths without forking the framework.

If this fails, OpenJarvis should be dropped despite its feature breadth.

If it succeeds cleanly, its security/durability scores may improve enough to justify further consideration.

### MAF / LangGraph uncertainty

Both remain credible fallbacks. Their current research evidence is sufficient to defer hands-on work until the higher-value uncertainties above are resolved.

## 8. Prototype decision

To minimize experimental work, prototype **two architectural extremes first**:

1. **PydanticAI** — provisional matrix leader and cleanest Ada-owned architecture.
2. **OpenJarvis** — highest reuse upside and highest material uncertainty.

This is not selecting OpenJarvis over the higher-scoring MAF or LangGraph. It is testing the uncertainty most likely to change the decision.

### Prototype A — PydanticAI recovery slice

Build only:

`local model → typed action proposal → Ada Guard → fake calendar side effect → effect record → crash → resume`

Acceptance questions:

- Does the runtime preserve enough stable state to resume safely?
- Can Ada guarantee no duplicate side effect after a crash between provider commit and tool-result return?
- Can authoritative Ada Memory remain completely outside runtime persistence?
- Is remote observability fully absent in the local profile?

### Prototype B — OpenJarvis Guard-boundary slice

Register one Ada-owned privileged fake calendar adapter and exercise it through:

- normal agent execution,
- scheduler/background execution,
- MCP entry,
- server/API entry.

Acceptance questions:

- Can every actual side effect be forced through the same Ada Guard?
- Is there any supported path that bypasses the Ada adapter?
- Can built-in fact memory and external analytics be disabled cleanly?
- How much of OpenJarvis' scheduler/server/local-engine infrastructure remains useful once Ada Guard and Ada Memory replace the critical boundaries?
- Is a fork required?

## 9. Decision rule after prototypes

- **If PydanticAI validates:** it remains the default candidate unless OpenJarvis demonstrates a clearly lower lifetime implementation/maintenance burden without weakening the Guard boundary.
- **If OpenJarvis fails the Guard-boundary test or requires a substantial fork:** remove it from the shortlist.
- **If PydanticAI recovery proves insufficient:** prototype MAF next.
- **Use LangGraph next only if explicit durable workflow control becomes more valuable than the extra application infrastructure Ada must build.**
- **Minimal custom wins only if framework lifecycle/audit burden approaches the cost of maintaining the missing runtime functionality ourselves.**

## 10. ADR gate

Do **not** create the final ADR until the two targeted prototypes are evaluated.

The ADR must contain:

- hard-gate outcome,
- agreed weighted matrix,
- prototype evidence,
- selected option,
- rejected alternatives and why,
- consequences,
- version/pinning/privacy requirements,
- explicit re-open triggers.
