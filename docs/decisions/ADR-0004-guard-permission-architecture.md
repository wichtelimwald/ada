# ADR-0004: Use Cedar behind the Ada-owned Guard boundary

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Ada requires a deterministic authorization boundary before consequential side effects and sensitive disclosures.

The model may propose actions and explain them, but it must not:

- create or enlarge authority;
- treat forwarded, quoted, retrieved, tool, file, web or model content as permission;
- infer grants from learned behavior or prior success;
- decide that a provider effect succeeded;
- disclose private data merely because it can read it.

Ada keeps these concepts separate:

`Person != Data Subject != Audience != Authority`

Authentication is also separate from authorization. Channels/integrations establish identity, assurance and instruction-provenance claims; Ada Guard evaluates those claims against explicit grants and prohibitions.

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

After targeted prototypes, the final research scores are:

| Candidate | Score |
| --- | ---: |
| **Cedar** | **95** |
| Ada-owned typed evaluator | 94 |
| OPA / Rego | 83 |
| PyCasbin / Casbin | 76 |

## Prototype evidence

### Ada-evaluator control

A small standard-library-only evaluator passed the confirmed MVP permission cases without needing a general expression language.

This proved that Ada's MVP semantics are understandable and that Ada does not require a large IAM platform merely to express current permissions.

It also clarified the long-term risk: a custom evaluator would make Ada responsible for security-critical policy semantics, schema/tooling evolution and future relationship complexity.

### Cedar prototype

Cedar was then tested against the same authority model using:

```text
Ada AuthorizationRequest
        |
thin CedarGuard adapter
        |
cedarpy 4.12.0
        |
cedar-policy 4.12.0 Rust engine
        |
Ada GuardDecision
```

The tested `cedarpy` release is community-maintained and wraps the real Cedar Rust engine using PyO3/maturin.

On the target Python 3.14 / ARM64 environment, the final conformance run produced:

```text
Ran 10 tests in 0.031s

OK
```

The tested cases covered:

1. explicit calendar-create grant;
2. default deny;
3. explicit forbid overrides permit;
4. direct authenticated one-off approval;
5. forwarded content cannot approve;
6. model-originated "permission" cannot approve;
7. expired/revoked grants stop authorizing;
8. private busy-time may be disclosed while detailed private content remains denied;
9. malformed authorization request fails closed;
10. invalid Cedar policy/schema configuration is rejected before privileged use.

No Ada-owned Rust bridge and no policy sidecar were required.

## Decision

Use **Cedar as Ada's initial policy engine behind an Ada-owned Guard boundary**.

Ada owns:

- `AuthorizationRequest`;
- `GuardDecision`;
- authentication/assurance claims;
- instruction provenance;
- grant lifecycle and storage semantics;
- policy version/deployment;
- Action Ledger;
- provider outcome truth;
- application/domain authority semantics.

Cedar owns the policy evaluation semantics.

The initial private integration uses pinned `cedarpy`, which embeds the Cedar Rust engine into Python.

The architectural boundary remains:

```text
application / privileged provider path
        |
Ada AuthorizationRequest
        |
AdaGuard
        |
private Cedar adapter
        |
Cedar engine
        |
Ada GuardDecision
        |
Action Ledger / disclosure boundary
```

Provider adapters and application use cases must not depend directly on Cedar-native types.

## Why Cedar

Cedar aligns closely with Ada's authorization model:

- `principal`;
- `action`;
- `resource`;
- structured `context`;
- default deny;
- explicit `forbid` overriding permits;
- human-readable policies;
- schema validation;
- entity/relationship modeling;
- policy diagnostics and analysis tooling.

This lets Ada reuse a dedicated authorization engine rather than gradually growing an Ada-specific policy language.

## Authorization request

Ada's request semantics may include:

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

The private Cedar adapter maps these concepts to Cedar principal/action/resource/context and, where useful later, Cedar entities/relationships.

Not every field is required for every action.

Missing mandatory security context results in denial.

## Guard decision

Every security-relevant decision must expose at least:

- effect: allow or deny;
- deterministic Ada reason code;
- matched Ada grant/prohibition identifiers where applicable;
- policy/configuration version.

Cedar's engine-local policy IDs are not Ada's stable identifiers.

Ada-generated policies/grants should use unique, stable `@id` annotations derived from Ada-owned rule/grant IDs. The adapter maps Cedar determining-policy IDs through cedarpy's annotation diagnostics for audit/UI use.

## Fail-closed wrapper semantics

Ada is stricter than Cedar's generic engine behavior at the application boundary.

The adapter must deny when:

- the request is malformed;
- required Ada security context is missing;
- policy/schema loading or validation fails;
- Cedar returns no final decision;
- Cedar reports policy-evaluation errors in diagnostics;
- the adapter itself fails.

No provider/disclosure path may interpret an authorization error as permission.

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

Cedar evaluates active policies; it does not define Ada's grant-governance workflow.

Grant mutation is itself privileged.

For the MVP:

- broad/general/risky grants require direct local Ada interaction;
- simple one-off approvals may be bound to a concrete operation and accepted through an appropriately authenticated authorized channel;
- forwarded/quoted/model/tool/web/file content cannot create authority;
- revocation must affect subsequent evaluations without model cooperation.

The production grant store and policy-generation workflow remain Ada responsibilities.

## Disclosure authority

Action authority and disclosure authority use the same Guard boundary but different actions/resources as appropriate.

For example:

- `calendar.disclose.busy` may be permitted for a family audience;
- `calendar.disclose.detail` for the same private event may be forbidden.

This prevents "Ada can read it" from becoming "Ada may reveal it."

## Community Python integration

The initial integration uses `cedarpy` rather than an Ada-owned Rust bridge or a Cedar sidecar.

Reasons:

- direct Python integration;
- no extra local network/process failure mode;
- current Python 3.14 / ARM64 support;
- wraps the actual Cedar Rust engine;
- exposes diagnostics, schema validation and reusable policy/schema handles;
- conformance prototype passed on the target environment.

However, `cedarpy` is community-maintained rather than officially supported by the Cedar team.

Therefore Ada must:

- pin the exact tested version;
- review dependency/supply-chain changes during upgrades;
- run the full Guard conformance suite for every upgrade;
- avoid leaking cedarpy-native types into Ada application/domain code;
- keep a documented fallback integration path.

## Integration fallback order

If `cedarpy` becomes unsuitable while Cedar remains the desired policy model, prefer:

1. a reviewed local Cedar service/sidecar around the official engine;
2. a minimal Ada-owned PyO3 bridge to the official Rust engine;
3. another reviewed Cedar SDK/binding if the ecosystem changes.

The AdaGuard / AuthorizationRequest / GuardDecision contract must remain
stable when changing the Cedar integration. `AuthorizationRequest` now
requires callers to provide instruction provenance and channel explicitly;
there are no implicit `direct` or `local-chat` defaults. This deliberate
contract tightening applies to every backend: unknown provenance is denied,
and no backend may infer a trusted source from a missing field.

## Upstream strategy

Prefer contributing general-purpose improvements to `cedarpy` rather than maintaining an Ada-specific fork.

If Ada identifies a binding gap:

1. reproduce and characterize it;
2. discuss it upstream;
3. contribute a narrow implementation and tests where appropriate;
4. do not make Ada depend on unreleased fork-only behavior;
5. adopt only reviewed/pinned released versions.

## Consequences

### Positive

- mature authorization semantics rather than Ada-owned matching logic;
- direct fit for default deny and explicit forbids;
- schemas and validation;
- future relationship/entity modeling;
- richer policy tooling/analysis path;
- no sidecar required initially;
- no Ada-owned Rust bridge required initially;
- stable Ada-owned domain/security API remains independent of Cedar integration details.

### Negative

- a community-maintained Python binding becomes a root-security dependency;
- Cedar adds a Rust/native dependency inside the Python runtime;
- Ada still owns authentication, grant lifecycle, policy generation, audit semantics and Action Ledger;
- Cedar concepts must be carefully mapped so they do not replace Ada's domain model;
- binding upgrades require explicit security/conformance review.

## Alternatives considered

### Small Ada-owned typed evaluator

Passed the MVP conformance cases and remains a valid fallback/control.

Not selected because Cedar now has a proven low-friction Python path while avoiding long-term growth of Ada-owned authorization semantics, schema tooling and relationship logic.

### PyCasbin

Provides direct Python integration and mature RBAC/ABAC/ReBAC capabilities.

Not selected because Ada's provenance, audience, representation and assurance semantics rely more heavily on custom matcher/model configuration.

### OPA / Rego

Provides powerful general policy-as-code capabilities and sidecar/Wasm integration options.

Not selected because its policy/runtime machinery is materially larger than Ada's current need and has no advantage over the now-tested Cedar path for the core authorization model.

## Re-open triggers

Re-open this ADR if:

- cedarpy maintenance or release cadence becomes unsuitable;
- Python/ARM64 wheel support regresses;
- supply-chain review identifies unacceptable risk;
- Cedar cannot express a confirmed Ada permission cleanly;
- Ada starts adding substantial authorization semantics outside Cedar to compensate for engine limitations;
- a first-party Cedar Python SDK or better integration mode appears;
- process isolation becomes preferable for the Guard;
- a security incident/bypass undermines confidence in the selected integration.

## Follow-up

If accepted:

1. add Ada-owned authorization request/decision types to `src/ada/core`;
2. add pinned `cedarpy` to the runtime dependency set;
3. implement the thin Cedar adapter behind `AdaGuard`;
4. promote the conformance cases into the permanent test suite;
5. define initial Cedar schema and policy-generation conventions;
6. require unique Ada rule/grant IDs mapped through Cedar `@id`;
7. implement trusted grant storage/mutation separately;
8. integrate Guard before Action Ledger/provider writes and before sensitive disclosures;
9. update the threat model with the binding, grant-store and authentication-claim boundaries.
