# Results — Cedar Guard conformance probe

**Status:** First target-Mac run exposed adapter/API issues before Cedar policy evaluation; fixes applied, rerun pending.

## Target-Mac run 1

Environment successfully installed `cedarpy==4.12.0`, but all ten tests failed during `CedarGuard` construction before authorization.

Root cause:

- the experiment passed a reusable `PolicySet` handle to `validate_policies()`;
- in cedarpy 4.12.0, `validate_policies(policies, schema)` still requires policy **text** for `policies`;
- `PolicySet` reuse is supported by `is_authorized*`, while the reusable `Schema` handle is supported by `validate_policies()`.

Observed error:

```text
TypeError: 'PolicySet' object is not an instance of 'str'
while processing 'policies'
```

This was an experiment-adapter bug, not a Cedar authorization failure.

Fix applied:

1. validate original policy text against the reusable Schema;
2. only after successful validation, parse it into a reusable PolicySet for authorization;
3. declare the four Cedar schema actions individually using the shared RequestContext.

No conformance result is claimed from run 1 because no policy evaluation was reached.

## Dependency

- cedarpy: 4.12.0
- embedded cedar-policy engine: 4.12.0
- license: Apache-2.0
- integration: PyO3/maturin community binding

## Expected decision question

Can Ada replace the custom policy evaluator with a thin community Cedar binding while keeping:

- Ada-owned AuthorizationRequest / GuardDecision;
- default deny;
- forbid-overrides-permit;
- deterministic rule IDs;
- schema validation;
- fail-closed behavior;
- no service/IPC dependency?

## Pass criteria

- all conformance cases pass;
- Python 3.14/aarch64 installation succeeds in Ada's container profile;
- adapter stays mapping-only rather than re-implementing policy semantics;
- Cedar diagnostics can be mapped to Ada rule IDs/reason codes;
- validation failure cannot reach a privileged provider path.

## Re-open / fallback

If the community binding is not sufficiently maintainable or compatible, compare:

1. local Cedar sidecar around the official Rust engine;
2. tiny Ada-owned PyO3 bridge to the official engine;
3. small Ada evaluator as fallback/control.


## Target-Mac run 2

Cedar authorization itself behaved correctly in all ten tests.

Result:

- **7 tests passed**
- **3 tests failed only on expected rule-label assertions**
- all three failures returned the correct authorization decision and the correct determining Cedar policy, but `diagnostics.reasons` exposed parser-generated ids (`policy0`, `policy1`, `policy2`) rather than the human `@id(...)` annotations expected by the experiment.

This matches cedarpy 4.12.0's documented contract:

- `diagnostics.reasons` contains Cedar/parser policy IDs;
- `diagnostics.id_annotations_by_reason` maps those IDs to optional human-readable `@id` annotations.

The adapter now maps each determining Cedar policy ID through `id_annotations_by_reason`, falling back to the Cedar ID when no annotation exists.

This is diagnostics translation only; authorization semantics were already correct in run 2.

### Production implication

Ada-generated grants/policies should assign unique, stable `@id` values derived from Ada's own grant/rule identifiers. Cedar's internal policy IDs remain engine-local details.


## Target-Mac run 3 — final

After mapping Cedar's parser-generated policy IDs through `diagnostics.id_annotations_by_reason`, the complete conformance suite passed:

```text
Ran 10 tests in 0.031s

OK
```

Final result:

- **10/10 tests passed**
- Python 3.14 target path works
- cedarpy 4.12.0 installation works on the target Mac/container architecture
- real Cedar 4.12.0 authorization semantics satisfy the tested Ada MVP cases
- no sidecar required
- no Ada-owned Rust bridge required
- the Ada adapter remains mapping/fail-closed logic only

### Final experiment conclusion

Cedar via cedarpy is viable for Ada's Guard boundary and removes the strongest practical objection identified in the initial evaluation: Python integration complexity.

The experiment does not prove cedarpy is permanently risk-free. It does show that the current community binding is a sufficiently thin and functional integration layer to justify selecting Cedar while keeping AdaGuard stable and replaceable.
