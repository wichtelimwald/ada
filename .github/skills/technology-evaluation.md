# Skill: Technology evaluation

Use this skill before selecting frameworks or major dependencies for Ada's capabilities.

## Process

1. Define the capability in user terms, not technology terms.
2. Define must-have constraints and explicit non-goals.
3. Identify credible maintained alternatives; include a minimal/custom option where realistic.
4. Verify current facts from primary sources where practical.
5. Review code license, model/asset licenses, usage restrictions, governance, maintenance, security history, and distribution implications separately.
6. Document data flows and trust boundaries.
7. State runtime/process, IPC, packaging, startup, resource, and cross-capability integration assumptions.
8. Score only criteria agreed for this decision; do not invent weights to force a preferred result.
9. Prototype only the unknowns that materially affect the decision.
10. Before acceptance, check that the resulting set of capability choices forms a coherent installable stack.
11. Record the final choice, consequences, and explicit re-open triggers in an ADR.

## Default criteria pool

Select only relevant criteria from:

- privacy / data egress,
- security / privilege boundary,
- security history / response process,
- user experience and latency,
- local/offline capability,
- quality/accuracy,
- target-platform coverage,
- accessibility,
- resource use,
- maturity/maintenance,
- integration compatibility / complexity,
- API stability,
- testability/observability,
- license/distribution constraints,
- ecosystem lock-in,
- cost.

Use `docs/research/technology-evaluation-template.md`.
