# Technology evaluation — Action Ledger / recovery semantics

**Status:** Research framing complete; weights not yet agreed, so no scoring yet  
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

Likely operation record fields:

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
last_error_code?
```

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

## 7. Candidate storage approaches

### A — Ada-owned state machine + Python stdlib SQLite

Use Python's built-in `sqlite3` and explicit Ada-owned SQL/state transitions.

**Advantages**

- no new runtime dependency;
- SQLite provides transactional atomic commit;
- file-based, local, low-resource, easy backup/inspection;
- fits the single-host container-first MVP;
- explicit schema keeps the security-critical state model directly reviewable;
- WAL can improve reader/writer concurrency if later needed.

**Risks**

- Ada owns migrations and SQL;
- state-transition correctness must be thoroughly tested;
- careless transaction boundaries can break the intended guarantees.

### B — Ada-owned state machine + SQLAlchemy/SQLite

Same Ada semantics, but use an ORM/database toolkit.

**Advantages**

- migrations/query abstractions can become easier as schema grows;
- future database replacement is less invasive.

**Risks**

- additional dependency and abstraction in a small state machine;
- ORM behavior can obscure exact transaction/locking semantics;
- likely more machinery than the initial schema requires.

### C — Event-sourcing library + SQLite

Use a mature event-sourcing package and model operation transitions as events.

**Advantages**

- append-only history and recovery concepts are first-class;
- existing SQLite persistence.

**Risks**

- introduces event-sourcing architecture beyond Ada's current need;
- operation state and provider reconciliation are still Ada-specific;
- larger conceptual and dependency surface.

### D — PydanticAI/Harness persistence as Action Ledger

Use runtime persistence/checkpoints as the primary consequential-action store.

**Advantages**

- less additional persistence code.

**Hard problem**

Targeted recovery research already showed that runtime persistence cannot establish side-effect truth after a hard process death. Provider reconciliation and stable Ada operation identity remain necessary.

**Current interpretation:** useful runtime evidence, but not a viable source of truth for the Action Ledger.

## 8. SQLite evidence

SQLite transactions provide atomic commit semantics, including recovery from interrupted commits. Python 3.14's `sqlite3` module is part of the standard library and recommends explicit transaction control using the connection's `autocommit` behavior.

SQLite WAL mode is optional. It allows readers and writers to proceed with more concurrency but requires all processes using the database to be on the same host.

That constraint matches Ada's initial single-host runtime. WAL is not required merely to get atomic commit.

## 9. Agreed decision criteria

| Criterion | Weight | Why it matters |
| --- | ---: | --- |
| Recovery / duplicate-side-effect safety | **30%** | This is the primary purpose of the ledger. |
| Crash durability / atomic transition clarity | **20%** | State must survive abrupt termination predictably. |
| Maintainer simplicity / reviewability | **20%** | Security-critical code should remain understandable. |
| Privacy / data minimization | **10%** | Ledger data is sensitive operational history. |
| Local resource / portability fit | **10%** | Must fit M1/16 GB and later Linux/server deployment. |
| Replaceability / integration clarity | **10%** | Storage implementation must not become domain semantics. |
| **Total** | **100%** | |

## 10. Scoring

Scale:

- **5 — Excellent:** directly supports Ada's recovery contract with little compensating complexity.
- **4 — Good:** strong fit with bounded caveats.
- **3 — Adequate:** workable, but meaningful extra machinery or opacity remains.
- **2 — Weak:** significant mismatch with Ada's recovery or maintainability goals.
- **1 — Poor:** unsuitable as the Action Ledger source of truth.

| Criterion | Weight | A stdlib SQLite | B SQLAlchemy + SQLite | C event sourcing | D runtime persistence |
| --- | ---: | ---: | ---: | ---: | ---: |
| Recovery / duplicate-side-effect safety | 30% | **5** | **5** | **5** | 2 |
| Crash durability / atomic transition clarity | 20% | **5** | 4 | 4 | 2 |
| Maintainer simplicity / reviewability | 20% | **5** | 3 | 2 | 4 |
| Privacy / data minimization | 10% | **5** | **5** | 4 | 3 |
| Local resource / portability fit | 10% | **5** | 4 | 3 | **5** |
| Replaceability / integration clarity | 10% | **5** | 4 | 3 | 2 |
| **Weighted total / 100** | **100%** | **100** | **84** | **75** | **54** |

### Score rationale

**A — stdlib SQLite (100):** fits the single-host/container-first MVP without another dependency, exposes transaction boundaries directly, supports atomic state changes, and keeps the ledger schema small and reviewable. The score does not imply that SQLite alone creates exactly-once semantics; provider reconciliation remains mandatory.

**B — SQLAlchemy + SQLite (84):** preserves the same database guarantees, but adds an abstraction layer and dependency before the schema/query complexity justifies it. Revisit if migrations/query breadth become costly.

**C — event sourcing (75):** conceptually compatible with operation history, but adds a larger architectural model than the current requirement. Ada still must implement provider reconciliation and operation semantics.

**D — PydanticAI/runtime persistence (54):** useful supporting evidence, but prior crash tests already showed it cannot be the source of truth for external side effects. It cannot replace Ada-owned stable operation IDs and reconciliation.

## 10a. Evidence table

| Property | A stdlib SQLite | B SQLAlchemy + SQLite | C event sourcing | D runtime persistence |
| --- | --- | --- | --- | --- |
| Ada owns state semantics | yes | yes | partly shaped by library | no / framework-shaped |
| Atomic local transitions | yes | yes | yes | framework-dependent |
| Extra dependency | no | yes | yes | already present |
| Direct transaction visibility | strongest | medium | medium | weakest |
| Append-only history | simple extra table | simple extra table | native | runtime history, not action truth |
| Provider reconciliation still required | yes | yes | yes | yes |
| MVP complexity | lowest | medium | highest | deceptively low |
| Current hard-crash evidence | suitable by design | suitable by design | suitable if modeled correctly | insufficient as source of truth |

## 11. Prototype gate

Do not prototype every storage option.

The highest-value prototype is the smallest complete crash/recovery slice using option A:

1. create operation;
2. record Guard allow;
3. transition to executing;
4. fake provider commits using operation ID;
5. simulate crash before ledger commit;
6. restart;
7. discover in-flight operation;
8. reconcile provider;
9. record committed;
10. prove provider write count remains exactly one.

Also test:

- denied operation causes zero provider writes;
- illegal state transitions are rejected;
- two concurrent attempts cannot both claim the same operation;
- ambiguous provider without reconciliation support is not retried automatically.

If the direct SQLite implementation becomes awkward or migration/query needs dominate, revisit SQLAlchemy before adding more hand-written persistence machinery.

## 12. Direction before crash/recovery prototype

The agreed weighting and scoring support:

> **Ada-owned Action Ledger state machine persisted with Python stdlib SQLite, with provider reconciliation as a mandatory part of side-effect safety.**

SQLite is the initial persistence implementation, not the domain boundary.

The important architectural commitment is the state/recovery contract:

- stable Ada operation ID before provider execution;
- durable state transition before/after external calls;
- `executing` after restart is treated as ambiguous;
- reconcile before retry;
- automatic retry only when idempotency/reconciliation makes it safe;
- no framework persistence is accepted as external side-effect truth.

The next gate is the crash/recovery prototype.

## 13. Primary references

- Python 3.14 sqlite3 documentation: https://docs.python.org/3.14/library/sqlite3.html
- SQLite atomic commit: https://www.sqlite.org/atomiccommit.html
- SQLite WAL: https://www.sqlite.org/wal.html
- Python eventsourcing SQLite persistence: https://eventsourcing.readthedocs.io/
