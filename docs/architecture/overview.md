# Architecture overview — pre-decision

**Status:** Straw-man for trust-boundary discussion. No implementation architecture or component decomposition is selected.

This document records boundaries that must be considered during research. Boxes in the sketch are responsibilities, not necessarily separate processes, libraries, or services.

```text
User
  |
Interaction / UI
  |
Assistant reasoning / orchestration
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

Product discovery defines required capabilities and constraints first. Capability research then uses `docs/research/technology-evaluation-template.md`.

Before finalizing capability ADRs, check the combined stack for runtime/process, IPC, packaging, resource, security, privacy, and distribution compatibility. Decisions that materially affect boundaries, dependencies, portability, privacy, security, or packaging receive an ADR.
