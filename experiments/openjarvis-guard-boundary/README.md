# OpenJarvis Guard-boundary experiment

**Status:** disposable architecture experiment, not Ada production code.

## Question

Can Ada keep one deterministic side-effect boundary while reusing OpenJarvis execution paths?

The probe uses one Ada-owned calendar tool whose `execute()` method always calls `AdaGuard` before touching provider state.

It exercises:

1. direct `ToolExecutor`
2. MCP `tools/call`
3. a real OpenJarvis tool-using agent with a deterministic mock engine
4. the scheduler path
5. the canonical server/direct-operation helper

Each path is tested twice:

- **allowed**: exactly one guard check and one provider write
- **denied**: exactly one guard check and zero provider writes

## Important scope

This does **not** prove the entire OpenJarvis platform safe.

It answers a narrower architecture question:

> If Ada exposes only narrow Ada-owned privileged tools, can those tools keep the real authorization boundary inside the adapter regardless of which OpenJarvis execution path invoked them?

OpenJarvis framework policy remains defense in depth only.

## Fixed revision

The experiment pins OpenJarvis commit:

`b03203fb91e3c9a2a23815eb50d5e93b4c0ba4cc`

This is after the broad capability-enforcement fix researched for Ada.

## Python requirement

Current OpenJarvis metadata requires Python **>=3.10,<3.14**.

On the target Mac, use Python 3.13:

```bash
uv sync --python 3.13
uv run --python 3.13 python guard_boundary_probe.py
```

## Privacy note

The probe does not instantiate OpenJarvis `AnalyticsClient`.

It also records the current `AnalyticsConfig().enabled` default so the privacy-hardening requirement is explicit rather than hidden.

## Pass condition

For every tested execution path:

- allowed → `guard_checks == 1` and `provider_writes == 1`
- denied → `guard_checks == 1` and `provider_writes == 0`

If any path can create provider state without entering the Ada-owned tool/Guard, OpenJarvis fails this experiment.
