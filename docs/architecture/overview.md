# Architecture overview — pre-decision

**Status:** No implementation architecture selected.

This document records capability boundaries that should remain distinguishable during research. It does not prescribe frameworks or processes.

```text
User
  |
Interaction / UI
  |
Assistant orchestration
  |-------------------|
Memory / private data  Capability tools
                       |-- speech input/output
                       |-- computer control
                       |-- screen/camera (if selected)
                       |-- integrations
  |
Policy / permission boundary
  |
Local OS and optional external services
```

## Cross-cutting concerns

- privacy and data classification,
- deterministic permissions,
- cloud egress control,
- observability without sensitive logging,
- user-visible state and approvals,
- replaceability where it has practical value,
- recovery/undo for actions where feasible.

## Architecture decision process

Each major capability is researched independently using `docs/research/technology-evaluation-template.md`. Decisions that materially affect boundaries, dependencies, portability, privacy, or security receive an ADR.
