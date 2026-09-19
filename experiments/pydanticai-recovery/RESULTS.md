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

## Repeated local benchmark — first pass

A repeated benchmark with the 4k Qwen3 alias produced:

- warmup: 44.745 s
- measured runs: 45.003 s, 48.887 s, 56.352 s
- mean: **50.081 s**
- median: **48.887 s**
- all tool calls/results valid: yes

The corresponding OpenJarvis benchmark produced a mean of **8.619 s**.

### Important asymmetry discovered

This first repeated comparison is **not suitable for framework performance ranking**.

Source inspection showed:

- OpenJarvis' native Ollama engine explicitly sends `think=false` for Qwen3 by default.
- PydanticAI's Ollama provider uses Ollama's OpenAI-compatible API.
- The PydanticAI run did not disable unified thinking, and PydanticAI's own Ollama tests demonstrate Qwen3 returning a `ThinkingPart` by default.

Therefore the ~5.8x latency gap may largely measure **Qwen3 thinking mode**, not framework overhead.

The benchmark has been corrected to set:

`ModelSettings(thinking=False, temperature=0.0, max_tokens=256)`

Only the corrected rerun should be used for performance comparison.

## Repeated local benchmark — thinking disabled

Corrected rerun with:

- base model: `qwen3:8b`
- model alias: `ada-qwen3-8b-4k`
- context: 4096
- `thinking=false`
- temperature: 0
- max output tokens: 256
- 1 warm-up + 3 measured runs

Results:

- warmup: **44.241 s**
- run 1: **45.490 s**
- run 2: **55.423 s**
- run 3: **106.598 s**
- mean: **69.170 s**
- median: **55.423 s**
- tool calls valid: yes, exactly one each
- final answers correct: yes
- system stable: yes

### Interpretation

Disabling PydanticAI's unified thinking did **not** remove the large latency gap to OpenJarvis.

The current measurements are therefore:

- OpenJarvis native Ollama path: mean **8.619 s**, median **8.651 s**
- PydanticAI Ollama/OpenAI-compatible path: mean **69.170 s**, median **55.423 s**

This is a real target-machine observation, but it is **not yet evidence that PydanticAI itself adds ~47 seconds of framework overhead**.

The candidates use different Ollama protocol paths:

- OpenJarvis: native Ollama `/api/chat`
- PydanticAI: Ollama OpenAI-compatible `/v1/chat/completions`

Before attributing the difference to a framework, isolate the provider/API-path cost with one direct Ollama A/B probe.

## Final local benchmark — explicit Ollama reasoning disabled

Final rerun with the provider-specific setting:

`openai_reasoning_effort="none"`

and otherwise the same controlled profile:

- model: `ada-qwen3-8b-4k`
- context: 4096
- temperature: 0
- max output tokens: 256
- one warm-up + three measured runs

Results:

- warmup: **8.722 s**
- run 1: **7.711 s**
- run 2: **7.729 s**
- run 3: **7.720 s**
- mean: **7.720 s**
- median: **7.720 s**
- all tool calls valid: yes
- final answers correct: yes
- system stable: yes

### Root cause of the earlier slow runs

The earlier 45–106 s PydanticAI measurements were not caused by:

- PydanticAI framework overhead in general, or
- Ollama's OpenAI-compatible API path.

The framework-free API-path experiment measured native Ollama at 10.717 s mean and the OpenAI-compatible endpoint at 10.859 s mean.

The material difference was Qwen3 reasoning configuration. In PydanticAI 2.46.0, unified `thinking=False` did not disable reasoning for this local Qwen3/Ollama profile, while explicit `openai_reasoning_effort="none"` did.

This is a **provider-profile integration caveat**, not a structural local-performance disadvantage.

### Comparative local result

Under equivalent non-reasoning settings on the same target Mac:

- PydanticAI: **7.720 s mean / median**
- OpenJarvis: **8.619 s mean / 8.651 s median**
- direct Ollama native: **10.717 s mean**
- direct Ollama OpenAI-compatible: **10.859 s mean**

These tiny benchmark differences should not be used as a framework ranking criterion. The relevant conclusion is that both framework candidates provide acceptable local tool-calling performance on the M1/16 GB target when configured correctly.

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
