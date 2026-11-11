# Skill: Technology evaluation

Use this skill before selecting frameworks or major dependencies for Ada's capabilities.

## Process

1. Define the capability in user terms, not technology terms.
2. Define must-have constraints and explicit non-goals.
3. Identify credible maintained alternatives; include a minimal/custom option where realistic.
4. Verify current facts from primary sources where practical.
5. Apply the mandatory license/distribution gate below; do not treat unknowns as cleared.
6. Document data flows and trust boundaries.
7. State runtime/process, IPC, packaging, startup, resource, and cross-capability integration assumptions.
8. Score only criteria agreed for this decision; do not invent weights to force a preferred result.
9. Prototype only the unknowns that materially affect the decision.
10. Before acceptance, check that the resulting set of capability choices forms a coherent installable stack.
11. Record the final choice, consequences, and explicit re-open triggers in an ADR.

## Mandatory license and distribution gate

Before scoring a serious third-party candidate as viable, distinguish:

- Code, runtime, service, and SDK licenses; model weights, voices, datasets, and assets may have separate terms.
- Commercial use, hosting, copyleft/network-copyleft, attribution/NOTICE, trademarks, and redistribution/bundling restrictions.
- Fit with Ada's MIT-owned code, self-hosted use, and possible future deployment modes. Non-OSI licenses require an explicit trade-off, not automatic rejection.
- Provenance, maintenance, security response, privacy/egress, and transitive dependencies. Record unknowns rather than assuming clearance.

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
