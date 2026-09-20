# Technology evaluation — Guard / permission architecture

**Status:** Research complete — conformance prototype supports ADR-0004  
**Date checked:** 2026-09-20  
**Depends on:** ADR-0002, ADR-0003, representative MVP scenarios, threat model

## 1. User need

Ada must make consequential actions and sensitive disclosures only when a deterministic, independently enforceable permission exists.

The model may:

- understand a request;
- propose an action;
- explain why it thinks the action is useful.

The model may **not**:

- create authority;
- enlarge a grant;
- treat encountered content as permission;
- decide that a provider write succeeded;
- disclose private information merely because it can read it.

The Guard must therefore sit on every privileged action/disclosure path before the provider or recipient boundary.

## 2. Core security model

Ada keeps the distinction:

`Person != Data Subject != Audience != Authority`

Authorization is also distinct from authentication.

### Authentication

A channel/integration establishes claims such as:

- who the initiating actor is believed to be;
- how that identity was verified;
- which channel/session produced the request;
- whether quoted/forwarded content was separated from the direct instruction.

The Guard must not invent or upgrade these claims.

Example: the visible email `From` field alone is not sufficient authentication.

### Authorization

The Guard evaluates a concrete request against explicit Ada grants and prohibitions.

A useful conceptual request is:

```text
actor
action
resource
data_subjects
audience
purpose
channel + authentication assurance
instruction provenance
representation / acting-for
risk class
other deterministic context
```

Not every field is required for every action.

### Consequential action flow

```text
authenticated input / application context
        |
model or deterministic logic proposes action
        |
typed Ada AuthorizationRequest
        |
AdaGuard
        |
ALLOW / DENY + deterministic explanation
        |
ActionLedger
        |
provider adapter
```

### Sensitive disclosure flow

```text
permitted source data
        |
candidate response/context
        |
typed Ada DisclosureRequest
        |
AdaGuard
        |
ALLOW / DENY / REDACT
        |
audience/channel adapter
```

The MVP may implement action authorization before full disclosure filtering, but both belong to the same authority model.

## 3. Hard gates

Any selected design must satisfy all of these.

### G1 — Ada-owned boundary

Application/provider code calls Ada Guard, not a framework approval mechanism directly.

### G2 — Fail closed

Missing actor, action, resource, required context, invalid policy data, or evaluator failure results in denial for consequential operations.

### G3 — Default deny

No matching grant means no authority.

### G4 — Explicit deny wins

A prohibition must override a broader allow where both match.

### G5 — No authority from untrusted content

Websites, forwarded/quoted content, files, documents, tool output, retrieved text, and model output cannot create grants.

### G6 — Learning never expands authority

Memory, previous successful execution, model confidence, or learned behavior cannot automatically enlarge a permission.

### G7 — Revocation is effective

A revoked/expired grant must stop authorizing future operations without requiring model cooperation.

### G8 — Explainable decisions

For security-relevant decisions Ada can record at least:

- decision;
- request/action identifier;
- matched grant/prohibition identifiers or deterministic reason;
- policy/configuration version;
- relevant non-sensitive context.

The log must not require storing raw private prompts/content.

### G9 — Local/offline authorization

Guard evaluation requires no cloud service and no mandatory network egress.

### G10 — No arbitrary code as policy

Policy/grant data must not execute arbitrary Python, shell, template, or model-generated code.

### G11 — License/distribution compatibility

The chosen component must be distributable in Ada's permissive open-source architecture.

## 4. MVP authorization requirements

The product baseline currently establishes:

- start restrictively;
- expand authority only through explicit grants;
- recognized calendar creation may proceed inside a prior grant;
- arbitrary appointment deletion is not authorized;
- a simple one-off action may be approved through a direct instruction from an authenticated/authorized registered email sender;
- forwarded/quoted sections cannot grant authority;
- broad/general/risky grants require direct local Ada interaction;
- guardians have equal standing in the initial family model;
- children's authority may be granted narrowly and evolves separately;
- everyone, including children, may have private areas;
- responding to an unknown external sender requires approval;
- acting/sending on somebody's behalf requires an applicable explicit grant;
- reading the message archive requires explicit request;
- general terminal/install/purchase/financial authority is outside MVP.

Several details remain intentionally unresolved, including exact child/guardian governance, cancellation/delete scopes, and sender-authentication mechanisms.

## 5. Ada-owned authorization types

Regardless of policy engine, Ada should own its request and result semantics.

Conceptually:

```text
AuthorizationRequest
├── actor
├── action
├── resource
├── subjects
├── audience
├── purpose
├── provenance
├── channel_assurance
├── representation
└── deterministic context

GuardDecision
├── effect: allow | deny
├── reason_code
├── matched_rule_ids
├── policy_version
└── obligations / constraints (optional, later)
```

A policy backend must not leak its native request/result model into provider adapters.

## 6. Candidate architectures

### A — Small Ada-owned typed evaluator

Implement the initial evaluator directly in Ada/Python.

Policies/grants are structured data, not executable Python. The evaluator performs explicit deterministic matching and deny-overrides.

Possible initial rule shape:

```text
grant_id
effect: allow | deny
principal / actor selector
action selector
resource selector
audience / subject / purpose constraints
allowed channels / minimum assurance
valid_from / valid_until
representation constraints
```

#### Advantages

- exact fit to Ada's unusual semantics;
- no foreign policy language in the first MVP;
- no additional process/runtime;
- easy to keep MIT for Ada-owned code;
- small attack/dependency surface;
- easiest path to deterministic reason codes and tests;
- can evolve behind the stable AdaGuard boundary.

#### Risks

- authorization logic is security-critical code Ada must maintain;
- scope creep could accidentally create a poorly designed custom policy language;
- formal analysis/tooling is initially weaker than Cedar/OPA;
- must resist adding ad-hoc condition callbacks or arbitrary expressions.

#### Guardrail

Keep the evaluator intentionally small. If policy expressiveness grows beyond simple typed selectors/constraints, re-evaluate Cedar/other engines rather than inventing a general-purpose DSL.

---

### B — Cedar policy engine

Cedar is a purpose-built authorization language using a principal/action/resource/context request model. Policies support `permit` and `forbid`; authorization is denied when no permit applies or when an applicable forbid policy matches.

Cedar also has schema validation and policy-analysis tooling.

Code license: Apache-2.0.

#### Fit

Strong conceptual fit for:

- principal;
- action;
- resource;
- contextual constraints;
- explicit forbids;
- separate human-readable policy files;
- future policy analysis.

Ada-specific audience, data-subject, provenance, and representation semantics could be modeled as entities/context.

#### Integration caveat

The canonical Cedar implementation is Rust. The official Cedar organization currently provides Rust plus official Go/Java/JavaScript-related implementations/bindings; a direct first-party Python binding is not the primary integration path.

A third-party Python binding exists, but adopting an additional unofficial FFI binding for Ada's root authorization boundary would require its own supply-chain/security evaluation.

Alternative integration through a separate Cedar process/service would add IPC/lifecycle complexity.

#### Advantages

- excellent authorization semantics;
- deny-by-default / forbid behavior aligns well with Ada;
- analyzable, schema-driven policies;
- policy logic separated from application code;
- strong future option if Ada's permission model becomes large.

#### Risks

- awkward initial Python integration compared with a native library;
- Apache-2.0 dependency boundary;
- entity/schema model adds complexity before MVP policy breadth is known;
- Ada must still own authentication, audience semantics, grant lifecycle and action ledger.

---

### C — PyCasbin / Casbin

Casbin is an authorization library supporting ACL, RBAC, ABAC and ReBAC-style models. PyCasbin is available directly in Python.

Code license: Apache-2.0.

Casbin models can support deny-override and customizable request/matcher structures.

#### Advantages

- direct Python integration;
- mature access-control ecosystem;
- supports RBAC/ABAC/ReBAC patterns;
- policy persistence adapters and management APIs exist;
- no sidecar required.

#### Risks

- Ada's model is not primarily role-based;
- provenance, channel assurance, audience, data subjects and representation would likely become custom matcher inputs;
- complex matcher/configuration expressions may become harder to review than explicit Ada semantics;
- easy to inherit generic IAM concepts that are not actually needed for the family/MVP model.

---

### D — Open Policy Agent / Rego

OPA evaluates declarative Rego policies over structured input. It supports REST/sidecar integration and compiled WebAssembly policies.

Code license: Apache-2.0.

#### Advantages

- extremely expressive;
- mature general policy engine;
- JSON-shaped input can represent Ada's full request context;
- excellent ecosystem for policy-as-code;
- sidecar/process isolation is possible.

#### Risks

- substantially more policy/platform machinery than Ada needs today;
- Python integration typically implies REST sidecar or Wasm/community integration;
- separate policy bundle/engine lifecycle becomes another operational component;
- Rego's generality raises authoring/review complexity for a small household permission model;
- likely highest complexity tax among realistic MVP options.

## 7. Architectural option independent of engine

The engine choice should remain hidden behind Ada Guard.

```text
Ada application
    |
AdaGuard
    |
Ada AuthorizationRequest
    |
private PolicyEvaluator backend
    +-- initial typed evaluator
    +-- future Cedar backend
    +-- future other reviewed backend
```

The backend is a trusted security component, **not** a normal third-party plugin.

Changing the backend requires the Guard conformance/security test suite to pass.

## 8. Agreed decision criteria

Weights were agreed with the maintainer before scoring.

| Criterion | Weight | Why it matters |
| --- | ---: | --- |
| Bypass resistance / fail-closed security | **30%** | Guard is the last deterministic boundary before privileged effects/disclosures. |
| Semantic fit to Ada authority model | **20%** | Actor, audience, subject, provenance, representation and channel assurance must stay understandable. |
| Auditability / explainability / testability | **15%** | Users need to understand grants and Ada must prove why an action was allowed/denied. |
| Maintainability / simplicity | **15%** | Small maintainer budget; avoid a policy platform that exceeds the product need. |
| Extensibility / replaceability | **10%** | Ada will gain channels/capabilities without rewriting authority semantics. |
| Policy administration / human readability | **5%** | Grants need eventual understandable configuration and revocation. |
| License / dependency / integration fit | **5%** | Keep the stack distributable and the root security boundary auditable. |
| **Total** | **100%** | |

## 9. Evidence-based scoring

Scale:

- **5 — Excellent:** strongly fits Ada with little compensation.
- **4 — Good:** solid fit with bounded caveats.
- **3 — Adequate:** workable but meaningful compensation remains.
- **2 — Weak:** significant mismatch or integration burden.
- **1 — Poor:** unattractive for this security boundary.

| Criterion | Weight | A Ada evaluator | B Cedar | C PyCasbin | D OPA/Rego |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bypass resistance / fail-closed security | 30% | **5** | **5** | 4 | **5** |
| Semantic fit to Ada authority model | 20% | **5** | **5** | 3 | 4 |
| Auditability / explainability / testability | 15% | **5** | **5** | 4 | **5** |
| Maintainability / simplicity | 15% | 4 | **4** | **4** | 2 |
| Extensibility / replaceability | 10% | 4 | **5** | 4 | **5** |
| Policy administration / human readability | 5% | 4 | **5** | 4 | 4 |
| License / dependency / integration fit | 5% | **5** | 3 | 4 | 2 |
| **Weighted total / 100** | **100%** | **94** | **95** | **76** | **83** |

### Score rationale

**A — Ada evaluator (94):** highest fit because the MVP semantics are narrow but unusual, the evaluator can be fail-closed and deny-overrides without a general expression language, and the entire root security path stays directly auditable in the Python codebase. Its main risk is future scope creep into a home-grown policy DSL.

**B — Cedar (95):** strongest general authorization model and, after prototype evidence, also a practical Python fit. Cedar natively uses principal/action/resource/context, denies when no permit matches, and an applicable `forbid` overrides permits. The community-maintained `cedarpy` 4.12.0 binding wraps the real Cedar 4.12.0 Rust engine through PyO3, supports Python 3.14 / Linux aarch64 and macOS arm64, and provides authorization, diagnostics, schema validation and reusable policy/schema handles. Ada's full conformance probe passed without a sidecar or Ada-owned Rust bridge. The remaining penalty is that the Python integration layer is community-maintained rather than an officially supported Cedar SDK, so it requires pinning, supply-chain review and an explicit fallback path.

**C — PyCasbin (76):** mature and easy to embed in Python, with ABAC/ReBAC and deny-capable effect models. Ada's provenance, audience, representation and channel-assurance semantics would, however, become custom matcher/model configuration, making the root boundary less directly aligned with Ada's domain.

**D — OPA/Rego (83):** very strong general policy engine with REST and Wasm integration choices, but the operational/policy-language complexity is high for Ada's present scope. Python-first integration typically means another process or a Wasm/community layer.

The A-vs-B result is deliberately close. The prototype removed enough of Cedar's Python-integration penalty to make Cedar the preferred initial engine by a narrow margin. The small Ada evaluator remains a useful control/fallback, not the selected production direction.

## 9a. Evidence summary

| Property | A Ada evaluator | B Cedar | C PyCasbin | D OPA/Rego |
| --- | --- | --- | --- | --- |
| Python integration | native Ada code | community cedarpy binding over official Rust engine; tested on Python 3.14/ARM64 | native | no primary Python embedding path |
| Default-deny achievable | yes | yes, native model | yes | yes |
| Explicit deny override | yes, implement directly | yes, native `forbid` | yes, model-dependent | yes |
| Ada-specific semantics | exact | model via entities/context | custom matcher/model | arbitrary structured input |
| Human-readable policy | structured Ada data | strong | model + policy files | strong but Rego learning curve |
| Formal/schema analysis | initially low | strongest | moderate | strong tooling |
| Extra process required | no | no with cedarpy; optional sidecar later | no | common sidecar option |
| Complexity for MVP | lowest | medium | medium | highest |
| General future expressiveness | intentionally bounded | high | high | very high |

## 10. Typed-evaluator conformance prototype

The targeted prototype implemented a standard-library-only evaluator with:

- Ada-owned typed authorization request;
- typed allow/deny rules;
- actor, action, resource, subject, audience and purpose selectors;
- provenance and channel selectors;
- minimum authentication assurance;
- representation / acting-for selector;
- validity interval and revocation;
- default deny;
- explicit deny override;
- deterministic reason codes;
- sorted matched rule IDs;
- policy version in every decision.

It deliberately did **not** implement arbitrary expressions, callbacks, roles, inheritance, relationship graphs, generic boolean syntax or model-written policies.

### Conformance results

All nine tested cases passed:

1. explicit recognized calendar-create grant -> allow;
2. same action without grant -> default deny;
3. explicit deny overrides broad allow;
4. direct authenticated one-off approval -> allow;
5. forwarded instruction cannot approve;
6. model-originated "permission" cannot approve;
7. revoked/expired grants stop authorizing;
8. private busy-time may be disclosed to family while detailed private content is denied;
9. malformed request fails closed.

The same evaluator logic was executed with Python 3.13.5 on Linux x86_64 without third-party dependencies.

### Prototype interpretation

The predefined Cedar-escalation condition was **not triggered**.

The confirmed MVP permission cases remain understandable with typed selectors and constraints. No generic policy language is required.

The prototype validates the evaluator shape, not the complete authorization subsystem. Production still needs:

- trusted grant/policy storage and mutation paths;
- authentication claims established outside the Guard;
- local-only creation path for broad/risky grants;
- audit persistence;
- Action Ledger integration;
- tests that every privileged provider/disclosure path passes through Ada Guard;
- schema/rule validation and safe migration/version handling.

## 11. Cedar conformance prototype

Because the initial recommendation was challenged on long-term reuse grounds, Cedar was tested against the same Ada Guard semantics.

### Integration path tested

```text
Ada AuthorizationRequest
        |
thin Ada CedarGuard adapter
        |
cedarpy 4.12.0
        |
cedar-policy 4.12.0 Rust engine
        |
Ada GuardDecision
```

No Ada-owned Rust bridge or policy sidecar was required.

### Binding evidence

The tested `cedarpy` release:

- wraps the real Rust `cedar-policy` engine via PyO3/maturin;
- supports Python 3.14;
- publishes Linux aarch64 and macOS arm64 wheels;
- exposes authorization diagnostics;
- supports reusable PolicySet and Schema handles;
- validates policies against Cedar schemas;
- supports batch authorization and policy-template linking.

It is Apache-2.0 and community-maintained, not officially supported by the Cedar team.

### Target-Mac runs

Run 1 exposed an experiment bug: `validate_policies()` expects policy text rather than a reusable PolicySet handle. The adapter was corrected to validate policy text first and then parse/reuse PolicySet for authorization.

Run 2 reached Cedar authorization. Seven tests passed; three failed only because the test expected human `@id` labels directly in `diagnostics.reasons`. Cedarpy intentionally exposes parser policy IDs there and provides `diagnostics.id_annotations_by_reason` as the label mapping.

The adapter was corrected to translate Cedar determining-policy IDs to Ada-facing stable rule labels.

Run 3:

```text
Ran 10 tests in 0.031s

OK
```

### Conformance result

All tested requirements passed:

1. explicit recognized calendar-create grant;
2. default deny;
3. explicit forbid overrides permit;
4. direct authenticated one-off approval;
5. forwarded content cannot approve;
6. model-originated content cannot approve;
7. expired/revoked grants stop authorizing;
8. private busy-time vs detailed disclosure;
9. malformed request fails closed;
10. invalid policy/schema configuration is rejected before privileged use.

The Ada wrapper additionally treats any Cedar evaluation diagnostic error as fail-closed denial.

### Adapter scope

The Ada adapter remains intentionally thin. It owns:

- mapping Ada AuthorizationRequest to Cedar principal/action/resource/context;
- policy/schema loading and validation;
- fail-closed interpretation of Cedar errors;
- translating Cedar diagnostics into Ada GuardDecision / stable rule references.

It does **not** implement authorization matching semantics itself.

## 12. Research conclusion

The weighted evaluation plus both conformance prototypes now support:

> **Ada keeps AdaGuard / AuthorizationRequest / GuardDecision as stable Ada-owned boundaries and uses Cedar as the initial policy engine, integrated through the pinned community `cedarpy` binding.**

The reason Cedar now narrowly outranks the custom evaluator is that the prototype eliminated most of the practical Python integration cost while retaining Cedar's advantages:

- mature policy semantics instead of Ada-owned security logic;
- schemas and policy validation;
- future relationship/entity modeling;
- richer analysis/tooling path;
- default deny and forbid-overrides-permit as engine semantics;
- clean future transition to another Cedar integration mode without changing Ada's public Guard boundary.

The `cedarpy` package is an **integration dependency, not Ada's architectural boundary**.

If that community layer becomes unsuitable, Ada can preserve the Cedar policy model and switch the private backend to:

1. a reviewed local Cedar service/sidecar around the official engine;
2. a minimal Ada-owned PyO3 bridge to the official engine;
3. another reviewed Cedar SDK as ecosystem support evolves.

The small Ada evaluator remains a regression/control implementation and emergency fallback concept; it is not the preferred production path.

## 13. Community / upstream strategy

Prefer upstream collaboration over an Ada-specific cedarpy fork.

If Ada encounters a small general-purpose binding gap:

1. reproduce it independently;
2. open an upstream issue/design discussion;
3. contribute a narrowly scoped implementation and tests when appropriate;
4. do not make Ada depend on unreleased fork-only behavior;
5. pin released versions and run the Ada Guard conformance suite during upgrades.

One observed API consistency opportunity is that `is_authorized*` supports reusable PolicySet handles while `validate_policies()` currently accepts policy text plus a reusable Schema handle. This is not an Ada blocker and should only be proposed upstream if the maintainers consider PolicySet validation useful.

## 14. Re-open triggers

Re-open this decision if:

- cedarpy maintenance or release cadence becomes unsuitable for a root security dependency;
- supported Python/ARM64 wheels regress;
- supply-chain review finds an unacceptable risk;
- Cedar semantics cannot express a confirmed Ada authorization requirement cleanly;
- Ada starts implementing substantial authorization logic outside Cedar to compensate for engine limitations;
- a first-party Cedar Python SDK or materially better integration path becomes available;
- process isolation becomes desirable enough to prefer a local Cedar sidecar;
- a security incident/bypass undermines confidence in the selected integration.

## 15. Primary references

- Cedar language/reference: https://docs.cedarpolicy.com/
- Cedar implementation: https://github.com/cedar-policy/cedar
- Cedar authorization algorithm: https://docs.cedarpolicy.com/auth/authorization.html
- cedarpy community binding: https://github.com/k9securityio/cedar-py
- Open Policy Agent / Rego: https://www.openpolicyagent.org/docs/policy-language
- OPA integration options: https://www.openpolicyagent.org/docs/integration
- OPA WebAssembly: https://www.openpolicyagent.org/docs/wasm
- Casbin documentation: https://casbin.org/docs/overview
- PyCasbin: https://github.com/casbin/pycasbin
