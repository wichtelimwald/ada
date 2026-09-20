# ADR-0004: Use an Ada-owned typed Guard evaluator

- **Status:** Proposed
- **Date:** 2026-09-20

## Context

Ada requires a deterministic authorization boundary before consequential side effects and sensitive disclosures.

The model may propose actions and explain them, but it must not:

- create or enlarge authority;
- treat forwarded, quoted, retrieved, tool, file, web or model content as permission;
- infer grants from learned behavior or prior success;
- decide that a provider effect succeeded;
- disclose private data merely because it can read it.

Ada also keeps these concepts separate:

`Person != Data Subject != Audience != Authority`

Authentication is separate from authorization. Channels/integrations establish identity and assurance claims; Ada Guard evaluates those claims against explicit grants and prohibitions.

The evaluated options were:

1. small Ada-owned typed evaluator;
2. Cedar;
3. PyCasbin / Casbin;
4. Open Policy Agent / Rego.

Agreed decision weights:

| Criterion | Weight |
| --- | ---: |
| Bypass resistance / fail-closed security | 30% |
| Semantic fit to Ada authority model | 20% |
| Auditability / explainability / testability | 15% |
| Maintainability / simplicity | 15% |
| Extensibility / replaceability | 10% |
| Policy administration / human readability | 5% |
| License / dependency / integration fit | 5% |

Final research scores:

| Candidate | Score |
| --- | ---: |
| **Ada-owned typed evaluator** | **94** |
| Cedar | 91 |
| OPA / Rego | 83 |
| PyCasbin / Casbin | 76 |

## Prototype evidence

A targeted typed-evaluator prototype exercised the MVP permission semantics without third-party dependencies or a general expression language.

The evaluator supported:

- actor;
- action;
- resource;
- data subjects;
- audience;
- purpose;
- instruction provenance;
- channel;
- authentication assurance;
- representation / acting-for;
- validity window;
- revocation;
- allow/deny;
- default deny;
- explicit deny override;
- deterministic reason codes;
- matched rule IDs;
- policy version.

All tested conformance cases passed:

1. an explicitly granted calendar create is allowed;
2. the same action without a grant is denied;
3. an explicit deny overrides a broader allow;
4. a direct authenticated one-off approval can authorize the matching operation;
5. forwarded content cannot approve;
6. model-originated "permission" cannot approve;
7. revoked/expired grants stop authorizing;
8. private busy-time may be visible to a family audience while detailed private content remains denied;
9. malformed authorization requests fail closed.

The prototype did not need:

- arbitrary expressions;
- Python callbacks or predicates in policy data;
- role inheritance;
- relationship graph traversal;
- general boolean policy syntax;
- framework-native policy objects.

The predefined escalation condition to prototype Cedar was therefore not triggered.

## Decision

Use an **Ada-owned typed policy evaluator behind the stable AdaGuard boundary** for the initial MVP.

The evaluator is intentionally not a general-purpose policy engine.

The stable boundary is:

```text
application / provider path
        |
AuthorizationRequest
        |
AdaGuard
        |
private typed PolicyEvaluator
        |
GuardDecision
```

Provider adapters and application use cases depend on Ada-owned authorization types, not evaluator-internal rule structures.

## Authorization request

Ada owns the authorization request semantics.

The initial request model may include:

```text
actor
action
resource
data_subjects
audience
purpose
instruction provenance
channel + authentication assurance
representation / acting-for
deterministic context
```

Not every field is required for every action.

Missing required security context causes denial.

## Guard decision

Every security-relevant decision must provide at least:

- effect: allow or deny;
- deterministic reason code;
- matched grant/prohibition identifiers where applicable;
- policy/configuration version.

The audit layer may record additional non-sensitive context, but raw prompts or private content are not required for authorization explainability.

## Evaluation semantics

The initial evaluator must satisfy:

1. **default deny:** no matching grant means deny;
2. **deny overrides allow:** any matching explicit prohibition wins;
3. **fail closed:** malformed requests, policy failures or missing mandatory context deny consequential operations;
4. **no executable policies:** grants/rules are structured data, never arbitrary Python, shell, templates or model-generated code;
5. **revocation/expiry:** inactive grants cease authorizing without model cooperation;
6. **no learning-based authority:** memory, confidence and previous success cannot expand authority;
7. **provenance-aware approval:** direct authenticated instructions may satisfy a grant where forwarded/quoted/model content cannot;
8. **audience-aware disclosure:** permission to read/store data is distinct from permission to reveal it to an audience.

## Authentication boundary

Ada Guard does **not** authenticate senders or sessions.

Channel adapters establish claims such as:

- actor identity;
- verification method / assurance;
- channel/session;
- direct vs forwarded/quoted provenance.

The Guard consumes these claims but cannot upgrade them.

The visible email `From` field alone is not an authorization grant and is not sufficient authentication by itself.

## Grant creation and mutation

The evaluator only evaluates policy/grant data. It does not define who may create or modify that data.

Grant mutation is itself privileged.

For the MVP:

- broad/general/risky grants require direct local Ada interaction;
- simple one-off approvals may be bound to a concrete operation and accepted through an appropriately authenticated authorized channel;
- forwarded/quoted/model/tool/web/file content cannot create grants;
- revocation must be immediately effective for subsequent evaluations.

The production grant store and mutation workflow remain implementation work.

## Disclosure authority

Action authorization and disclosure authorization use the same Ada authority concepts but may expose different actions/resources.

For example:

- `calendar.disclose.busy` may be permitted for a family audience;
- `calendar.disclose.detail` for the same private event may be explicitly denied.

This prevents "the assistant could read it" from becoming "the assistant may reveal it."

## Cedar escalation strategy

Cedar is the preferred escalation engine if the small evaluator stops being small.

Re-open this ADR before adding:

- arbitrary boolean/expression syntax;
- complex policy inheritance;
- substantial group/relationship traversal;
- capability-specific evaluator special cases;
- policy analysis/schema requirements that would duplicate a mature policy engine.

A future Cedar backend must remain behind the same AdaGuard / AuthorizationRequest / GuardDecision boundary.

The Guard conformance suite becomes mandatory for any replacement evaluator.

## Consequences

### Positive

- exact semantic fit to Ada's MVP authority model;
- no additional runtime/process/FFI dependency in the root authorization path;
- directly auditable Python implementation;
- deterministic decisions and tests;
- MIT project-owned implementation;
- easy integration with the current modular monolith;
- policy engine remains replaceable.

### Negative

- Ada owns security-critical authorization code;
- less formal policy/schema tooling than Cedar initially;
- discipline is required to prevent gradual growth into a custom DSL;
- grant storage, administration, authentication and audit persistence still need separate design/implementation;
- relationship-heavy future authorization may require migration to Cedar.

## Alternatives considered

### Cedar

Semantically an excellent fit. Cedar's principal/action/resource/context model, default deny and forbid-overrides-permit behavior align closely with Ada.

Not selected initially because the MVP does not yet need Cedar's broader policy machinery and the Python-first Ada runtime does not currently have an equally simple canonical first-party authorizer embedding path.

Cedar remains the first escalation option.

### PyCasbin

Provides direct Python integration and mature RBAC/ABAC/ReBAC capabilities.

Not selected because Ada's authority semantics would rely heavily on custom matcher/model configuration for provenance, audience, representation and assurance.

### OPA / Rego

Provides powerful general policy-as-code capabilities and strong integration options through REST or Wasm.

Not selected because its policy/runtime machinery is materially larger than the current household/MVP authorization need.

## Re-open triggers

Re-open this ADR if:

- the evaluator needs arbitrary expression syntax;
- roles/groups/relationships become difficult to model with simple typed selectors;
- authorization accumulates capability-specific branches;
- the evaluator becomes too large for comprehensive review and conformance tests;
- policy administration requires stronger static/schema analysis;
- a mature supported Cedar Python path materially reduces integration cost;
- a security incident/bypass undermines confidence in the custom evaluator.

## Follow-up

If accepted:

1. promote Ada-owned authorization request/decision types into `src/ada/core`;
2. implement the small evaluator under the Guard boundary;
3. add the conformance cases to the permanent test suite;
4. implement trusted grant storage/mutation separately;
5. integrate Guard before the Action Ledger/provider path;
6. add disclosure-authorization tests before family/private briefings;
7. update the threat model with the grant store and authentication-claim boundaries.
