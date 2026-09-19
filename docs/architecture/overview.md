# Architecture overview

**Status:** Product scope is confirmed and ADR-0002 is accepted. Ada uses a modular core with replaceable infrastructure adapters; several capability and deployment decisions remain open.

This document records the high-level trust boundaries. Boxes in the sketch are responsibilities, not necessarily separate processes, libraries, or services. The current modular implementation boundary is defined in [`modular-core-boundaries.md`](modular-core-boundaries.md).

```text
User
  |
Interaction / UI
  |
Assistant application / orchestration
  |
Replaceable agent-runtime adapter
  |
  +---------------- Policy / permission boundary ----------------+
  |                                                              |
Persisted memory / private data                         Capability interfaces
                                                      |-- speech
                                                      |-- computer actions
                                                      |-- screen/camera (if selected)
                                                      |-- integrations
  |                                                              |
  +--------------------- local trust boundary --------------------+
                                  |
                     Optional privacy / egress boundary
                                  |
                         External services (if any)
```

The policy boundary must mediate privileged reads/writes and actions. Remote transmission, if introduced, must pass an explicit egress/privacy boundary rather than being an incidental property of a capability.

## Cross-cutting concerns

- privacy and data classification,
- deterministic permissions,
- cloud-egress control,
- observability without sensitive logging,
- user-visible state and approvals,
- replaceability where it has practical value,
- recovery/undo for actions where feasible,
- process/runtime topology, IPC, packaging, startup behavior, and update strategy,
- integration compatibility between separately evaluated capabilities.

## Architecture decision process

Product discovery defines required capabilities and constraints first. Capability research then uses `docs/research/technology-evaluation-template.md`. ADR-0002 selected PydanticAI as the initial replaceable agent-runtime adapter, not as Ada's application architecture.

Before finalizing capability ADRs, check the combined stack for runtime/process, IPC, packaging, resource, security, privacy, and distribution compatibility. Decisions that materially affect boundaries, dependencies, portability, privacy, security, or packaging receive an ADR.
