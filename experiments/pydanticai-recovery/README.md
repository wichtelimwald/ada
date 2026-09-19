# PydanticAI recovery experiment

**Status:** disposable architecture experiment, not Ada production code.

## Question

Can PydanticAI plus `StepPersistence` provide useful recovery state while Ada keeps the real side-effect guarantee in its own deterministic boundary?

The experiment deliberately separates:

1. **Runtime persistence** — PydanticAI / `StepPersistence`.
2. **Authorization** — a tiny deterministic `AdaGuard`.
3. **Side-effect truth** — an Ada-owned action ledger.
4. **External state** — a fake calendar provider that can be reconciled by a stable Ada operation id.

This mirrors the proposed Ada rule:

`LLM proposal → Ada Guard → Ada action ledger → provider adapter`

## Why two crash modes?

`StepPersistence` documents an append-only event log, continuable snapshots, and a tool-effect ledger. It also documents unresolved tool effects as `unknown_after_crash`.

A Python exception can still run framework error hooks. A true process death cannot.

The probe therefore tests:

- **exception-after-provider-commit** — framework failure hooks can run;
- **hard-exit-after-provider-commit** — the process terminates with `os._exit()` immediately after the fake provider committed the event.

The second case is intentionally harsher and is the more important architectural boundary.

## Fixed versions

- `pydantic-ai-slim[openai] == 2.46.0`
- `pydantic-ai-harness == 0.31.0`

These are research pins, not an Ada dependency decision.

## Run

From this directory:

```bash
uv sync
uv run python recovery_probe.py all
```

The command runs both crash modes in isolated directories and prints a JSON summary.

Expected safety property:

> The fake calendar contains exactly one event after recovery, even if the first process died after the provider committed but before the agent received the tool result.

The experiment is successful only if this is achieved **without treating PydanticAI approval or persistence as authorization**.

## Optional local-model smoke test

The recovery probe uses a deterministic `FunctionModel` so model quality cannot mask runtime/recovery behavior.

After the recovery behavior is understood, run the separate local Ollama smoke test on the real M1/16 GB machine:

```bash
export ADA_OLLAMA_MODEL='<installed tool-capable Ollama model>'
uv run python ollama_smoke.py
```

This tests only local tool-calling compatibility and latency. It is not required to evaluate the crash semantics.

## Interpretation

- If the exception case resumes but hard-exit does not, that is **not automatically a PydanticAI failure**. It means Ada needs a durable workflow engine or an Ada-owned recovery/reconciliation layer for real process death.
- If the Ada action ledger plus provider reconciliation prevents duplicate effects in both cases, PydanticAI remains viable even if `StepPersistence` cannot itself reconstruct every hard-killed run.
- If safe recovery requires fragile framework internals or duplicate-prone retries, lower PydanticAI's durability/reuse score before the ADR.
