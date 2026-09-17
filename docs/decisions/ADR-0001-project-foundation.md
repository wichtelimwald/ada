# ADR-0001: Project foundation before implementation

- **Status:** Accepted
- **Date:** 2026-09-17

## Context

Ada combines personal data, model reasoning, persistent memory, and potentially privileged computer control. Early framework choices can unintentionally determine privacy, licensing, platform, and security properties before the actual product scope is understood.

Mark LIV is a useful UX/product reference but is licensed CC BY-NC 4.0, while Ada's project-owned code is intended to use MIT.

## Decision

1. Start with product discovery and capability requirements before application implementation.
2. Keep major capability choices open until researched and compared using a documented decision matrix.
3. Use ADRs for decisions that materially affect architecture, trust boundaries, dependencies, platform strategy, privacy, security, or distribution.
4. Treat Mark LIV as clean-room UX inspiration only; do not copy its source code or assets.
5. Keep project-owned code MIT and preserve third-party license obligations separately.
6. Use local validation; do not add GitHub Actions unless explicitly approved later.
7. Keep the initial agent/skill set intentionally small.

## Consequences

### Positive

- Reduces premature lock-in.
- Makes privacy/security constraints visible before implementation.
- Creates an auditable basis for framework choices.
- Avoids incompatible reuse from Mark LIV.

### Negative

- Delays implementation while product scope and key decisions are researched.
- Requires maintaining decision and threat-model documentation.

## Alternatives considered

### Fork Mark LIV and harden it

Rejected as the default path because its CC BY-NC 4.0 license conflicts with the intended permissive MIT project strategy for a derived codebase, and its current architecture would carry assumptions we have not selected.

### Select the proposed stack immediately

Rejected because UI, memory, speech, agent, computer-control, and model choices depend on unresolved product requirements.
