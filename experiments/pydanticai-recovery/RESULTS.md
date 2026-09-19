# Results — PydanticAI recovery experiment

**Status:** Recovery experiment executed successfully on the target MacBook Air M1 / 16 GB. Local Ollama smoke test still pending.

## Environment

- macOS / Apple M1 / 16 GB
- Python 3.14.6
- pydantic-ai: 2.46.0
- pydantic-ai-harness: 0.31.0
- observability: off
- deterministic `FunctionModel` for recovery semantics

The shell had an unrelated pre-existing `VIRTUAL_ENV` pointing at another project. `uv` correctly ignored it and created the experiment-local `.venv`.

## Exception-after-side-effect

- Exit code: 1 from the deliberately injected exception
- StepPersistence run record present: yes
- Unresolved tool effect present: no; framework error handling converted the in-flight effect to a terminal state
- Complete snapshot available before recovery: no
- Interrupted snapshot available before recovery: yes
- Provider event count before recovery: 1
- Provider event count after recovery: 1
- Ada action status before recovery: `executing`
- Ada action status after recovery: `committed`
- Resume source: StepPersistence interrupted snapshot
- Duplicate side effect: no
- Result: **safe**

## Hard-exit-after-side-effect

- Exit code: 86 from deliberate `os._exit()`
- StepPersistence run record present: yes
- Unresolved tool effect present: yes, status `started`
- Stored idempotency key: `calendar-school-appointment-001`
- Complete snapshot available before recovery: no
- Interrupted snapshot available before recovery: no
- Provider event count before recovery: 1
- Provider event count after recovery: 1
- Ada action status before recovery: `executing`
- Ada action status after recovery: `committed`
- Resume source: fresh run after non-continuable crash
- Duplicate side effect: no
- Result: **safe**

## Main finding

PydanticAI / StepPersistence does **not** by itself provide an exactly-once guarantee for external side effects.

The hard-exit case is particularly important:

- StepPersistence durably retained the run record and an unresolved tool-effect record including the Ada operation id.
- No continuable snapshot survived the abrupt process death.
- Safe recovery therefore came from Ada-owned semantics: stable operation id, action ledger, and reconciliation against provider state.
- Recovery created a fresh PydanticAI run, found the already-created provider event by operation id, marked the Ada action committed, and did not create a duplicate.

This validates the intended separation:

`runtime persistence ≠ authorization ≠ action ledger ≠ provider state`

StepPersistence adds useful evidence and workflow context, but **Ada remains responsible for idempotency and side-effect truth**.

## Local Ollama smoke test

Executed on the target M1 / 16 GB Mac with a 4k-context alias of the same local Qwen3 model used for the OpenJarvis comparison.

- base model: `qwen3:8b`
- test alias: `ada-qwen3-8b-4k`
- context: 4096
- framework: PydanticAI 2.46.0
- Python: 3.14.6
- observability: off
- tool selected correctly: yes
- arguments valid: yes
- final answer correct: yes
- end-to-end latency: **45.140 s**
- system stability: stable
- output: correctly identified the 15:00 / 15:15 conflict and 25-minute travel-time issue

The run ended with a probe-only reporting error after successful model/tool execution because the script called `result.usage()` although this version exposes `result.usage` as an object. The probe code has been corrected. This does not invalidate the tool-call or latency result.

### Performance caution

Do not rank frameworks from this single measurement.

Current one-shot values are:

- OpenJarvis: 34.612 s
- PydanticAI: 45.140 s

The model may have different warm/cold-cache state between runs. Use repeated warm runs before drawing a performance conclusion.

## Decision impact

### Useful MVP reuse

**Score remains 3/5.**

The experiment confirms that StepPersistence contributes useful run/effect state, but Ada still needs its own action ledger and provider-reconciliation semantics. PydanticAI therefore saves meaningful runtime glue without eliminating the critical recovery layer.

### Durability / recovery / side-effect safety

**Score remains 4/5 and is now evidence-backed.**

Why not 5/5:

- exception recovery can continue from an interrupted snapshot;
- hard process death can leave no continuable snapshot;
- exactly-once external effects still require Ada-owned idempotency/reconciliation.

Why it remains strong:

- run identity survives;
- unresolved effects survive hard process death;
- idempotency metadata survives;
- clean recovery composition with an Ada-owned ledger is possible without framework-internal patches.

### Security-boundary fit

**No score change: 5/5.**

The experiment did not rely on PydanticAI approval for authority. The real side-effect path was guarded by Ada code.

### Maintainability observation

The core experiment used public APIs only. No PydanticAI internals were patched or subclassed.

However, `pydantic-ai-harness` is still a 0.x/alpha package and its own documentation allows minor-release API changes. Ada should pin versions and isolate Harness usage behind a small adapter if selected.

## ADR implication

The prototype **supports keeping PydanticAI in the lead**. It does not justify increasing the provisional weighted score yet.

The key architectural consequence is now evidence rather than assumption:

> Selecting PydanticAI would still require an Ada-owned action ledger and provider reconciliation layer. StepPersistence is useful runtime evidence and recovery support, not the source of side-effect truth.

The remaining PydanticAI experiment is the local Ollama/tool-calling smoke test on the same target machine.
