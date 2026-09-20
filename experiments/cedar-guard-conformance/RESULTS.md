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
