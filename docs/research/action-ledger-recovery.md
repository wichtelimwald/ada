# Technology evaluation — Action Ledger / recovery semantics

**Status:** Research active — weights agreed; custom control passed; mature durable-execution candidates added  
**Date checked:** 2026-09-20  
**Depends on:** ADR-0002, ADR-0003, ADR-0004, representative scenarios S1/S2

## 1. User need

Ada needs a durable record of consequential operations so that a crash, timeout, provider ambiguity, or model/runtime retry does not silently produce duplicate real-world effects.

The Action Ledger is the source of truth for Ada's own operation state. It is not:

- model memory;
- agent-runtime persistence;
- a provider's source of truth;
- a general analytics/event platform.

## 2. Required semantics

Every consequential operation receives a stable Ada operation ID before provider execution.

Minimum state model:

```text
proposed
  |
  +--> denied
  |
  +--> authorized
          |
          +--> executing
                  |
                  +--> committed
                  +--> failed
                  +--> ambiguous
```

Interpretation:

- **proposed** — typed action exists; no authority/execution implied.
- **denied** — Guard denied; provider must not be called.
- **authorized** — Guard allowed; provider not yet called.
- **executing** — provider call may be in flight or may have happened.
- **committed** — provider effect is confirmed.
- **failed** — known failure before/without provider commit.
- **ambiguous** — provider may have committed; must reconcile before retry.

A process restart that finds an operation in `executing` must treat it as recovery work equivalent to an ambiguous outcome. It must not blindly repeat the provider call.

## 3. Exactly-once boundary

The ledger alone cannot guarantee exactly-once effects in an external system.

Ada can safely automate retry only when at least one of these is true:

1. the provider accepts Ada's stable operation ID as a true idempotency key; or
2. the provider can reliably reconcile/search the attempted operation using stable Ada/provider metadata.

If neither is available, an ambiguous operation must stop for explicit/manual resolution rather than risk a duplicate.

Therefore the practical goal is:

> **exactly-once where the provider supports idempotency/reconciliation; otherwise never silently trade uncertainty for a duplicate side effect.**

## 4. Crash points to handle

The first vertical slice must test at least:

### C1 — crash before provider call

Ledger says `authorized`; no provider effect occurred.

Recovery may safely continue to provider execution.

### C2 — crash after `executing` is persisted but before provider receives the call

Ledger cannot prove whether the call reached the provider.

Recovery reconciles first.

### C3 — provider commits, process crashes before ledger records `committed`

Ledger remains `executing`.

Recovery reconciles and records the existing provider effect rather than creating a second one.

### C4 — provider returns explicit non-commit failure

Ledger records `failed`.

Retry policy may create a new attempt only under explicit operation semantics.

### C5 — provider timeout / connection loss after request transmission

Ledger records or recovers as `ambiguous`.

Reconcile before any retry.

## 5. Data model principles

Store the minimum structured data needed for recovery and audit.

Likely operation record/view fields:

```text
operation_id
action_kind
state
created_at
updated_at
policy_version
guard_reason
proposal_digest
provider_kind
provider_reference?
provider_outcome?
business_outcome?
last_error_code?
```

Provider outcome and business outcome are intentionally different.

For example:

- a phone provider reporting `call completed` proves a technical call outcome;
- it does **not** prove that an appointment was successfully booked;
- an order API returning a durable order ID can prove provider acceptance, while later delivery/cancellation is a separate business state.

The ledger must never claim a stronger outcome than the provider or another verifiable source actually proves.

The ledger may need a minimal structured action envelope for deterministic recovery, but it must not become a copy of:

- raw chat history;
- full model prompts;
- forwarded emails/documents;
- authoritative long-term Memory.

A separate append-only transition table may record state changes and timestamps without full private content.

## 6. Provider contract

A consequential provider adapter must expose enough semantics for recovery.

For the current CalendarPort this means:

- create with Ada operation ID / provider idempotency metadata where supported;
- reconcile an attempted create by operation ID or provider reference;
- distinguish confirmed commit, confirmed non-commit, and unresolved ambiguity.

The provider adapter must not report `committed` merely because the API call returned without a local exception.

## 7. Candidate architecture approaches

The initial research framed this too narrowly as a database choice. The custom SQLite prototype and maintainer review showed that the broader problem belongs to the **durable execution / workflow recovery / idempotency** domain.

SQLite remains a valid control implementation, but mature durable-execution systems must be compared before Ada owns this machinery.

### A — Ada-owned state machine + Python stdlib SQLite (control)

Ada directly implements operation states, compare-and-set transitions, recovery discovery, transition history and provider reconciliation. SQLite is only the persistence backend.

**Advantages**

- no runtime dependency;
- exact Ada semantics and privacy minimization;
- direct, reviewable transaction boundaries;
- small resource footprint;
- proven viable by the hard-crash control experiment.

**Risks**

- Ada owns security/recovery-critical state-machine code;
- Ada owns schema migrations, concurrency behavior and recovery evolution;
- future durable waiting, scheduling, signals and long-running workflows would add more custom machinery.

### B — DBOS durable execution library

DBOS is an MIT-licensed Python durable-execution library. It runs in-process rather than requiring a separate workflow server.

Current evidence:

- Python >=3.10 including Python 3.14;
- stable release 2.31.1 checked 2026-09-20;
- SQLite can be the system database and is the default for local/simple deployments;
- workflows resume from the last completed durable step;
- stable workflow IDs act as idempotency keys for workflow invocation;
- workflow/step status is inspectable;
- native PydanticAI durable-execution integration exists.

**Important boundary**

DBOS steps that call external providers are still at-least-once across a crash that occurs after the external effect but before the step checkpoint. External provider calls therefore still require Ada operation IDs plus idempotency/reconciliation.

**Advantages**

- removes much custom recovery/checkpoint machinery;
- in-process Python fit;
- SQLite-first local path matches Ada's current topology;
- MIT;
- existing PydanticAI integration may later reduce duplicated durability glue;
- supports durable sleep, messages, events and human-in-the-loop patterns that Ada is likely to need.

**Risks**

- durable workflow semantics/decorators can leak into Ada if not isolated;
- larger dependency set than stdlib SQLite;
- DBOS persists workflow inputs, workflow outputs and step outputs in its system database; Python uses pickle-based serialization by default;
- provider/business outcome semantics remain Ada-owned;
- DBOS recommends Postgres for general production deployments, while Ada's initial single-host personal runtime is intentionally evaluating whether SQLite remains sufficient.

### Ada privacy constraint if DBOS is selected

DBOS durable state must be treated as privacy-sensitive operational state, not as Ada Memory.

Do not pass/store raw:

- full email/message bodies;
- model prompts/transcripts;
- private documents;
- secrets/tokens;
- authoritative long-term Memory

as workflow or step inputs/outputs merely for convenience.

Prefer minimal recovery envelopes such as:

```text
operation_id
action_kind
provider_kind
provider_reference?
opaque content/store reference?
minimal typed outcome
```

If durable recovery needs sensitive content, store it in the appropriate Ada-owned encrypted/private store and pass only a stable reference through DBOS where practical.

### C — Restate durable execution runtime

Restate provides durable execution, keyed state, workflows, timers/signals and a PydanticAI integration. The self-hosted runtime is a separate single binary and does not require an external database.

**Advantages**

- purpose-built durable execution;
- strong recovery/orchestration primitives;
- PydanticAI integration;
- can grow into long-running/human-approval workflows.

**Risks**

- additional runtime process and operational boundary;
- Restate server uses BSL 1.1 rather than an OSI-open-source license; Python SDK is MIT;
- more infrastructure than Ada currently needs;
- still cannot manufacture exactly-once external-provider effects without idempotency/reconciliation.

### D — Temporal

Temporal is a mature durable workflow platform with Python support and strong crash/recovery semantics.

**Advantages**

- mature, well-established durable execution;
- strong observability, workflow history and long-running workflow support;
- self-hosted or managed deployment.

**Risks**

- separate service/worker architecture is heavy for Ada's single-host MVP;
- larger operational footprint and conceptual surface;
- provider idempotency/reconciliation remains necessary for external effects.

### E — Lower-level ORM/event-sourcing/runtime-persistence variants

SQLAlchemy+SQLite, event-sourcing libraries, and PydanticAI/Harness persistence remain useful references but are no longer primary candidates:

- SQLAlchemy changes storage abstraction, not the durable-execution problem;
- event sourcing gives history but does not by itself solve external side-effect recovery;
- PydanticAI persistence already failed as a standalone source of external side-effect truth in the hard-crash experiment.

## 8. Reference-system evidence

### OpenJarvis

OpenJarvis currently has several adjacent mechanisms:

- SQLite-backed scheduled-task persistence and task-run logs;
- an append-only SQLite security audit log with a hash chain;
- an EventBus for lifecycle events.

These are useful references for scheduling/audit, but no general provider-side-effect Action Ledger with durable idempotency/reconciliation was found.

Its cross-device example explicitly notes that stable task IDs do not themselves provide durable deduplication or exactly-once delivery, and calls out persistent task state, action idempotency and timeout reconciliation as future requirements before retrying uncertain writes.

### Mark LIV

Only public product/README behavior is considered because Mark LIV is a clean-room product/UX reference for Ada.

Its public README documents an Undo stack for local reversible actions and says desktop organization journals file moves so they can be reversed.

No public evidence used here shows a crash-durable external-provider transaction/reconciliation system. This is an undo/reversibility mechanism, not evidence of exactly-once external action recovery.

## 9. License / distribution hard gate

License and distribution fit is evaluated before scoring.

Current candidate status:

| Candidate | License / distribution status | Gate |
| --- | --- | --- |
| Ada-owned control | follows Ada project license | pass |
| DBOS Python | MIT | pass |
| Temporal OSS server / Python SDK | MIT | pass |
| Restate Python SDK | MIT | pass |
| Restate runtime/server | BSL 1.1 with production-use grant; change license Apache-2.0 after the defined change period | conditional |

Restate is not automatically excluded: its current BSL additional-use grant permits ordinary production deployments of workflows owned by the licensee. However, it is not an OSI open-source runtime today and restricts offering a public Restate platform service. That makes distribution, ecosystem expectations, and future hosted-platform use an explicit architectural cost for Ada.

Any future candidate must pass the same license/distribution gate before final scoring.

## 10. Agreed decision criteria

| Criterion | Weight | Why it matters |
| --- | ---: | --- |
| Recovery / duplicate-side-effect safety | **30%** | This is the primary purpose of the ledger. |
| Crash durability / atomic transition clarity | **20%** | State must survive abrupt termination predictably. |
| Maintainer simplicity / reviewability | **20%** | Security-critical code should remain understandable. |
| Privacy / data minimization | **10%** | Durable execution state is sensitive operational history. |
| Local resource / portability fit | **10%** | Must fit M1/16 GB and later Linux/server deployment. |
| Replaceability / integration clarity | **10%** | Durable infrastructure must not become Ada's domain semantics. |
| **Total** | **100%** | |

## 11. Final scoring

The DBOS target-Mac hard-crash prototype is complete, so the reopened comparison can now be scored.

Scale:

- **5 — Excellent:** strongly satisfies Ada with low compensating cost.
- **4 — Good:** strong fit with bounded caveats.
- **3 — Adequate:** workable, but meaningful complexity or mismatch remains.
- **2 — Weak:** substantial lifetime cost for Ada's MVP.
- **1 — Poor:** unattractive for this role.

| Criterion | Weight | Custom SQLite control | DBOS 3.0.0 | Restate | Temporal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Recovery / duplicate-side-effect safety | 30% | **5** | **5** | **5** | **5** |
| Crash durability / atomic transition clarity | 20% | **5** | **5** | **5** | **5** |
| Maintainer simplicity / lifetime reviewability | 20% | 3 | **5** | 3 | 2 |
| Privacy / data minimization | 10% | **5** | 3 | 3 | 3 |
| Local resource / portability fit | 10% | **5** | 4 | 3 | 2 |
| Replaceability / integration clarity | 10% | **4** | **4** | 3 | 3 |
| **Weighted total / 100** | **100%** | **90** | **92** | **80** | **74** |

### Score rationale

**DBOS 3.0.0 — 92:** wins narrowly because the target-Mac experiment proves the required hard-crash recovery path while DBOS removes substantial custom machinery for workflow checkpointing, restart recovery, durable waiting/signals/queues, and stable workflow identity. It stays in-process and can use SQLite, so it fits Ada's container-first single-host MVP. The main penalties are durable payload persistence/privacy and a larger dependency surface.

**Custom SQLite control — 90:** technically excellent for the narrow first slice and provides the smallest privacy/resource footprint. The penalty is lifetime maintenance: Ada would gradually own retries, recovery orchestration, durable waiting, signals, scheduler-like behavior, concurrency, schema migration and workflow evolution. Given Ada's limited maintainer budget, that is a meaningful long-term cost even though the initial implementation is small.

**Restate — 80:** strong durable-execution semantics and a good AI/PydanticAI story, but requires a separate runtime process and currently places the server under BSL 1.1. That is a real packaging/operational/license cost for Ada's initial personal single-host product.

**Temporal — 74:** mature and permissively MIT licensed, with excellent durability, but its service/worker architecture is substantially heavier than Ada currently needs.

### Important scoring boundary

All four approaches still require provider-specific idempotency/reconciliation for external side effects.

The score therefore does **not** reward claims of generic "exactly once" for arbitrary external APIs. The DBOS negative test explicitly demonstrated the boundary: an uncheckpointed unreconcilable provider step executes again after recovery and can duplicate the effect.

## 12. Custom SQLite control prototype

A standard-library-only prototype exercised the critical crash window:

```text
authorized
 -> executing (durable)
 -> provider commits
 -> os._exit()
 -> restart sees executing
 -> provider reconciliation
 -> committed
```

Result: **5/5 tests passed**.

Validated:

- provider commit followed by hard process death recovers without a duplicate effect;
- denied action creates zero provider effects;
- illegal transitions are rejected;
- stale concurrent transition cannot double-claim the operation;
- provider with no reconciliation capability becomes `ambiguous` and is not blindly retried.

The fake provider deliberately supports stable operation identity/reconciliation. This experiment does not claim SQLite can create exactly-once semantics for an arbitrary external provider.

## 13. DBOS target-Mac prototype

DBOS 3.0.0 was executed on the target Mac / Python 3.14.6.

Result:

```text
Ran 3 tests in 21.110s

OK
```

The hard-crash cases showed:

1. **Reconcilable provider:** DBOS retried the uncheckpointed step after restart; provider attempt count became 2 but real provider effect count stayed **1** because Ada operation identity/provider reconciliation found the existing effect.
2. **Unreconcilable provider:** DBOS retried the uncheckpointed step and produced **2** external effects. This intentionally proves the external-provider boundary.
3. **Completed workflow replay:** using the same Ada operation ID as DBOS workflow ID returned the durable result without another provider attempt.

### Experiment conclusion

DBOS can replace a substantial amount of Ada-owned recovery/checkpoint/workflow plumbing.

It cannot replace Ada's semantic Action Ledger responsibilities:

- provider capability classification;
- provider outcome;
- business outcome;
- `ambiguous` state;
- reconcile-before-retry rule;
- privacy-safe audit representation.

Therefore the intended boundary is:

```text
Ada Action Ledger semantics
        |
Ada DurableActionPort
        |
DBOS adapter (initial)
        |
provider adapter
        |
external system
```

For providers without safe idempotency/reconciliation, the Ada adapter must not expose DBOS' raw at-least-once retry behavior as a safe consequential action. Recovery must resolve to `ambiguous` / explicit handling instead of blindly repeating the external effect.

## 14. Research conclusion

The evidence supports:

> **Ada keeps an Ada-owned Action Ledger semantic boundary and uses DBOS as the initial durable-execution substrate behind it.**

This is deliberately different from "DBOS is the ledger."

Ada owns the meaning of operations and outcomes. DBOS owns workflow checkpointing/recovery mechanics.

The custom SQLite implementation remains the control/fallback if DBOS later becomes unsuitable.

A separate Ada operation/audit view may be needed even with DBOS, but it should contain only Ada-specific semantics and minimal privacy-safe references rather than duplicate the full DBOS workflow journal.

## 15. Architectural invariant independent of implementation

Whichever implementation wins:

- Ada owns the operation ID and semantic action/outcome model;
- Guard decision remains separate;
- technical provider outcome is separate from business outcome;
- an external provider's uncertain write is reconciled before retry;
- no durable-execution framework may reinterpret an unknown provider outcome as success;
- authoritative user Memory remains separate from workflow/ledger state;
- only minimal data required for recovery/audit should be persisted.

## 16. Primary references

- Python 3.14 sqlite3 documentation: https://docs.python.org/3.14/library/sqlite3.html
- SQLite atomic commit: https://www.sqlite.org/atomiccommit.html
- SQLite WAL: https://www.sqlite.org/wal.html
- DBOS Python documentation: https://docs.dbos.dev/python/programming-guide
- DBOS system database: https://docs.dbos.dev/explanations/system-tables
- DBOS license: https://github.com/dbos-inc/dbos-transact-py/blob/main/LICENSE
- DBOS PydanticAI integration: https://docs.dbos.dev/integrations/pydantic-ai
- Restate: https://restate.dev/
- Restate runtime license: https://github.com/restatedev/restate/blob/main/LICENSE
- Restate PydanticAI integration: https://restate.dev/blog/durable-orchestration-for-ai-agents-with-restate-and-pydantic-ai
- Temporal: https://docs.temporal.io/
- Temporal open-source project: https://temporal.io/
- OpenJarvis: https://github.com/open-jarvis/OpenJarvis
- Mark LIV public README: https://github.com/FatihMakes/Mark-LIV/blob/main/readme.md
