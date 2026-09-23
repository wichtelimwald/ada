# ADR-0005: Use DBOS behind Ada action/outcome semantics

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Ada needs durable recovery for consequential external actions such as calendar writes, sending messages, future computer control, and other real-world side effects.

A durable workflow engine can recover execution after crashes, but it cannot by itself establish the truth of an external provider outcome.

The critical crash window is:

```text
provider commits external effect
        |
process crashes before local durable checkpoint
        |
recovery re-enters unfinished work
```

If the provider offers neither idempotency nor reconciliation, replaying the external call can duplicate the real-world effect.

Therefore Ada distinguishes:

- execution durability;
- provider outcome truth;
- business outcome truth.

The evaluated primary approaches were:

1. Ada-owned durable state machine + stdlib SQLite;
2. DBOS 3.0.0;
3. Restate;
4. Temporal.

Agreed weights:

| Criterion | Weight |
| --- | ---: |
| Recovery / duplicate-side-effect safety | 30% |
| Crash durability / atomic transition clarity | 20% |
| Maintainer simplicity / lifetime reviewability | 20% |
| Privacy / data minimization | 10% |
| Local resource / portability fit | 10% |
| Replaceability / integration clarity | 10% |

Final scores after targeted prototypes:

| Candidate | Score |
| --- | ---: |
| **DBOS 3.0.0** | **92** |
| Ada-owned SQLite control | 90 |
| Restate | 80 |
| Temporal | 74 |

## Evidence

### Custom SQLite control

A standard-library-only control implementation passed the critical hard-crash case:

- operation durably moved to executing;
- provider committed;
- process died via `os._exit()`;
- restart reconciled the provider;
- operation became committed;
- provider effect count remained exactly one.

It also proved:

- denied actions create zero provider effects;
- illegal transitions are rejected;
- stale double claims are rejected;
- unreconcilable outcomes remain ambiguous rather than being blindly retried.

This proves the Ada-owned design is technically viable.

### DBOS target-Mac probe

DBOS 3.0.0 was tested on the target Apple Silicon Mac with Python 3.14.6.

```text
Ran 3 tests in 21.110s

OK
```

The probe showed:

1. **Reconcilable provider:** the uncheckpointed DBOS step ran again after recovery, but provider reconciliation by Ada operation ID kept the real effect count at exactly one.
2. **Unreconcilable provider:** the step ran again and produced a second real effect, proving that DBOS does not create exactly-once semantics for arbitrary external providers.
3. **Stable workflow identity:** using the Ada operation ID as the DBOS workflow ID caused a completed invocation to replay its durable result without another provider attempt.

## Decision

Use **DBOS as Ada's initial durable-execution substrate behind Ada-owned action/outcome semantics**.

“Action Ledger” is a logical Ada domain concept, not a requirement for a separate Ada database or workflow engine.

This is not:

> Ada builds a second durable-execution system beside DBOS.

It is:

> Ada owns the meaning of operations and outcomes; DBOS initially owns durable execution/checkpoint/recovery plumbing. Provider-native idempotency/reconciliation is reused before Ada adds custom recovery mechanisms.

The boundary is:

```text
Ada action proposal
        |
AdaGuard
        |
Ada action/outcome semantics
        |
Ada DurableActionPort
        |
DBOS adapter
        |
provider adapter
        |
external system
```

## Ada-owned semantics

Ada owns at least:

- stable `operation_id`;
- action kind;
- Guard decision linkage;
- provider capability classification;
- provider reference;
- provider outcome;
- business outcome;
- `ambiguous` semantics;
- reconcile-before-retry rules;
- privacy-safe audit representation.

DBOS workflow status is execution evidence, not automatically provider/business truth.

These semantics may initially be represented through minimal typed DBOS workflow/step state plus Ada-owned types. A separate Ada persistence table is **not** required unless the implementation proves it necessary for audit, queryability, privacy separation, or provider reconciliation.

## Provider capability model

Before allowing automatic durable retry of a consequential external action, the provider integration must declare whether it supports:

1. a true idempotency key;
2. reliable reconciliation/search by Ada operation ID or durable provider reference;
3. neither.

### Idempotent/reconcilable providers

DBOS durable steps may be retried, provided the provider adapter uses the stable Ada operation ID and reconciliation/idempotency correctly.

Current primary-source evidence shows this is not hypothetical:

- Google Calendar lets clients choose the event ID specifically to prevent duplicate creation after a request succeeds in the Calendar backend but the client fails before receiving the response.
- Microsoft Graph exposes `transactionId` specifically to avoid redundant event-create POSTs on retry.
- CalDAV/iCalendar defines persistent globally unique UIDs; CalDAV also defines UID-conflict behavior and conditional creation with `If-None-Match: *`.
- Gmail send does not document an equivalent idempotency key. A stable RFC822 `Message-ID` can be searched after an ambiguous send, so positive reconciliation is possible; absence of a match is not automatically proof that the message was never sent and may remain `ambiguous`.

### Providers with neither capability

Ada must not expose the raw DBOS at-least-once retry behavior as safe.

The Ada durable-action adapter must reject an unsupported provider *before* any create attempt and report `failed` / `not attempted`. If an external effect has already been attempted and its result cannot be established, recovery must instead resolve to `ambiguous` / manual handling, without blindly repeating that effect. These states must remain distinguishable in the user-facing response.

## Privacy

DBOS persists durable workflow state, including workflow inputs/outputs and step outputs.

Therefore DBOS state is privacy-sensitive operational state, not Ada Memory.

Do not pass raw:

- complete messages/emails;
- prompts/transcripts;
- private documents;
- secrets/tokens;
- authoritative long-term Memory

through DBOS simply for convenience.

Prefer minimal typed envelopes and stable references:

```text
operation_id
action_kind
provider_kind
provider_reference?
opaque content/store reference?
minimal typed outcome
```

If recovery requires sensitive content, keep the content in an appropriate Ada-owned private store and pass a stable reference where practical.

## Persistence

DBOS may use SQLite for Ada's initial local/single-host profile.

SQLite is an implementation choice inside the DBOS adapter, not the Ada domain boundary.

If later deployment requirements make another DBOS-supported system database preferable, Ada's action/outcome semantics must remain unchanged.

## Licensing

- DBOS Python: MIT — compatible at the top-level project-license level with
  Ada's MIT-owned code. This does **not** clear its transitive dependencies or
  any redistributed Ada artifact. DBOS 3.0.0 declares `psycopg[binary]>=3.1`;
  a combined Ada/Memory research installation on macOS resolved `psycopg`
  and `psycopg-binary` 3.3.6 (LGPL-3.0-only). The installed binary wheel
  contains bundled native libraries with their own license obligations.
  An Ada-only install and each intended release-platform artifact still need
  separate verification. See the [Psycopg installation options](https://www.psycopg.org/psycopg3/docs/basic/install.html)
  and [LGPLv3 terms](https://www.gnu.org/licenses/lgpl-3.0.html).
- Temporal: MIT — license gate passes, but operational complexity is higher.
- Restate Python SDK: MIT.
- Restate runtime/server: BSL 1.1 with an additional production-use grant and future Apache-2.0 change license; treated as a conditional fit rather than an automatic rejection.

Ada's initial release plan distributes its own source and a Dockerfile for
users to build locally, without publishing an Ada-built image or installer
containing dependencies. Before an Ada-built image/installer is published,
inventory the **exact Linux or other target artifacts**, inspect bundled
libraries, preserve applicable notices/license texts, provide required access
to covered source, and verify the applicable LGPL conditions. A general
license mention alone does not close that distribution gate. The distinction
between source distribution and bundled-artifact distribution applies to
the already accepted DBOS path as well as future components; it does not
change the DBOS technical decision. License fit remains a mandatory gate for
future durable-execution candidates.

## Consequences

### Positive

- reuses a mature durable-execution system instead of growing Ada-specific workflow infrastructure;
- in-process Python fit;
- Python 3.14 support;
- SQLite-capable local profile;
- stable workflow IDs map naturally to Ada operation IDs;
- durable restart/recovery, waiting, signals, queues and scheduling primitives become available;
- current PydanticAI integration may reduce duplicate durability glue later;
- custom SQLite control remains available as a fallback concept.

### Negative

- DBOS adds a non-trivial dependency set;
- durable workflow state must be treated as privacy-sensitive;
- DBOS semantics/decorators must be isolated behind Ada-owned interfaces;
- external provider safety still requires provider-specific idempotency/reconciliation handling, but Ada should reuse provider-native mechanisms rather than reimplement them;
- providers without safe reconciliation need explicit ambiguous/manual recovery handling;
- upgrades require crash/recovery regression testing.

## Alternatives considered

### Ada-owned SQLite state machine

Technically viable and only narrowly behind DBOS.

Not selected initially because Ada would own growing durable-execution mechanics such as recovery orchestration, durable waiting, signals, retries, workflow lifecycle and related migrations over the project lifetime.

Remains the fallback/control.

### Restate

Strong durable-execution primitives and good AI integration story.

Not selected initially because the separate runtime process increases local operational complexity and the current server license is BSL 1.1 rather than an OSI-open-source license.

### Temporal

Highly mature and MIT licensed.

Not selected because its service/worker architecture is substantially heavier than Ada's current single-host personal-assistant MVP.

## Re-open triggers

Re-open this ADR if:

- DBOS cannot implement Ada's unreconcilable-provider `ambiguous` rule without substantial custom state machinery;
- DBOS durable-state privacy cannot be constrained to acceptable minimal data;
- DBOS SQLite support proves unreliable for Ada's local profile;
- dependency/resource overhead becomes material on the target Mac;
- DBOS integration leaks widely into Ada domain/application code;
- upgrades repeatedly break durable behavior;
- Restate/Temporal or another system materially improves license/operational fit;
- Ada moves to a deployment topology where another durable-execution engine clearly fits better.

## Implementation follow-up

1. define Ada-owned `OperationId`, provider capability and outcome types;
2. define `DurableActionPort` independent of DBOS;
3. integrate DBOS 3.0.0 only behind its adapter;
4. for the first calendar adapter, map `OperationId` to the provider's native duplicate-prevention mechanism where supported;
5. promote hard-crash cases into permanent regression tests;
6. implement explicit unreconcilable-provider recovery to `ambiguous` only where provider-native idempotency/reconciliation is insufficient;
7. keep DBOS payloads minimal/privacy-safe;
8. add a separate Ada operation persistence/view only if DBOS state plus provider evidence proves insufficient;
9. update README with the plain-language user guarantee: Ada recovers actions after crashes but never claims or retries uncertain real-world outcomes blindly.
