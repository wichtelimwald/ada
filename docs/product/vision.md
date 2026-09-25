# Product vision

**Status:** Confirmed discovery baseline for the first MVP iteration.

The authoritative discovery artifact is [`interview-questionnaire.md`](interview-questionnaire.md). This file is only the short product summary.

## Product direction

Ada is a public, MIT-licensed, local-first and privacy-first personal AI assistant intended to feel like a capable household companion rather than a developer console.

The first real-world setting is a family. Adults and children should be able to contribute information and receive appropriate assistance while private context, audience, and authority remain distinct. Other households should be able to adopt the project, although developer-oriented setup is acceptable initially.

## Confirmed MVP

The first coherent MVP includes:

- local text chat,
- email intake and replies, including forwarded source material,
- calendar maintenance within explicit permission grants,
- scheduling-conflict detection including approximate travel time,
- personal and family briefings on request,
- persistent memory that is external to Ada, human-readable, directly editable, and correctable,
- deterministic permission enforcement independent of model decisions,
- private/shared scopes, action logging, correction, recovery, pause, and resume.

The MVP does **not** include speech, direct school-system integrations, autonomous conflict resolution, autonomous third-party coordination, broad computer control, project telemetry, or hidden persistent agent memory.

## Initial operating constraints

- First platform: macOS.
- First hardware: MacBook Air with Apple M1 and 16 GB RAM.
- Continuous availability is not required.
- Local chat and local-memory use should work offline.
- Local processing is preferred; remote processing requires appropriately scoped authorization and data minimization.
- Developer knowledge may be assumed for initial installation.
- Development and maintenance capacity is approximately one to two evenings per week.

## Development direction

Proceed through narrow end-to-end slices rather than selecting a comprehensive stack up front.

1. Preserve the confirmed discovery baseline.
2. Create representative family scenarios and expected outcomes.
3. Evaluate the smallest useful local path on the actual target hardware.
4. Make only architecture decisions required by the next working slice, using evidence, decision matrices, and ADRs.
5. Build and validate one complete journey before expanding scope.

## Still deliberately open

Foundational runtime, topology, Guard, durable-execution, local-model and
context-aware interpretation decisions are recorded in ADR-0002 through
ADR-0007. The following remain deliberately open or only partially decided:

- local interaction/UI implementation,
- authoritative Memory implementation,
- production email/calendar provider integration,
- optional remote-model assistance,
- remote-data boundary implementation,
- packaging/update and broader deployment strategy,
- speech/perception architecture,
- general computer control,
- detailed personal-context selection, calendar ownership, cancellation scopes,
  forgetting semantics, and offline integration behavior.

