# Results — Typed Guard conformance probe

**Status:** Passed.

## Validation environment

Independent execution of the same evaluator logic:

- Python: 3.13.5
- platform: Linux x86_64
- third-party dependencies: none

The evaluator is standard-library-only and contains no platform-specific behavior.

## Results

All nine conformance cases passed:

1. recognized calendar create with explicit grant -> **ALLOW**
2. same create without grant -> **DENY / no_matching_grant**
3. explicit deny plus matching allow -> **DENY / explicit_deny**
4. direct authenticated one-off approval -> **ALLOW**
5. forwarded instruction attempting the same approval -> **DENY**
6. model-originated "permission" -> **DENY**
7. revoked/expired grants -> **DENY**
8. private event busy-time disclosure to family -> **ALLOW**, detailed disclosure -> **DENY**
9. malformed authorization request -> **DENY / invalid_request**

Decisions also carry:

- deterministic reason code;
- sorted matched rule IDs;
- explicit policy version.

## Complexity result

The prototype did **not** require:

- arbitrary expressions;
- Python callbacks/predicates in policy data;
- roles or inheritance;
- relationship graph traversal;
- a generic boolean policy language;
- framework-native policy objects;
- network/process integration.

The permission cases remain expressible as typed selectors and constraints:

- actor;
- action;
- resource;
- data subjects;
- audience;
- purpose;
- provenance;
- channel;
- authentication assurance;
- representation / acting-for;
- validity interval;
- revocation.

## Security interpretation

The prototype validates the **policy-evaluation shape**, not the entire authorization system.

Still required in production:

- trusted rule/grant storage and mutation path;
- authentication/channel claims established outside the Guard;
- local-only path for broad/risky grant creation;
- audit persistence;
- Action Ledger integration;
- provider-side idempotency/reconciliation;
- rule/schema validation;
- tests proving every privileged adapter path calls Ada Guard.

## Cedar escalation assessment

The predefined escalation condition was **not triggered**.

The MVP cases do not currently justify adding a general policy language or a separate/FFI authorization engine.

Cedar remains the preferred escalation candidate if Ada later needs:

- complex relationship traversal;
- significant policy inheritance/group semantics;
- broad policy analysis/schema tooling;
- a larger policy administration surface;
- policy expressiveness that would otherwise require adding a custom expression language.

## Conclusion

The small Ada-owned typed evaluator is viable for the confirmed MVP permission semantics.

Proceed with it behind the stable AdaGuard boundary.

Do not evolve it into a general-purpose policy language.
