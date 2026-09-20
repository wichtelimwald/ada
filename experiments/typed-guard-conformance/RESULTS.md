# Results — Typed Guard conformance probe

**Status:** Prepared; execution result pending.

## Success criteria

- all conformance cases pass;
- evaluator remains understandable without arbitrary expressions or callbacks;
- decisions expose deterministic reason codes and matched rule IDs;
- explicit deny overrides allow;
- default behavior is deny;
- provenance/channel assurance can restrict approval paths;
- disclosure authority can be modeled independently from source-data readability.

## Escalation condition

If satisfying these cases requires adding a generic expression language, arbitrary predicates, inheritance machinery, or framework-native policy concepts to Ada's public Guard API, stop and prototype Cedar instead.
