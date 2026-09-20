# Results — Cedar Guard conformance probe

**Status:** Prepared; execution pending.

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
