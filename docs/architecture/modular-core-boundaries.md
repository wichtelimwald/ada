# Ada modular core boundaries

**Status:** Architecture baseline following accepted ADR-0002.

This document translates ADR-0002 into implementation boundaries without selecting a programming language, UI framework, memory backend, calendar provider, scheduler implementation, or packaging strategy.

The goal is not to create interfaces for every possible future feature. Ada defines a port only when it protects a trust boundary or keeps a decision-relevant dependency replaceable.

## 1. Architectural rule

> **Ada owns semantics; replaceable components implement ports.**

PydanticAI is the first agent-runtime implementation. It is not the application architecture.

Third-party components may be reused when useful, including isolated OpenJarvis functionality, but their concepts must not silently become Ada's domain model.

## 2. Core flow for consequential actions

```text
Input
  |
Ada application/use case
  |
AgentRuntimePort
  |  proposal only
  v
Ada action proposal
  |
AdaGuard
  |
ActionLedger
  |
Provider port
  |
External side effect
  |
Reconciliation / actual result
  |
Ada response + audit event
```

The model/runtime may propose an action. It may not authorize it or establish that it succeeded.

## 3. Stable Ada-owned concepts

The following concepts belong to Ada regardless of implementation technology.

### Actor and audience context

Represents who is interacting, whose data is involved, who may receive an answer, and which authority is applicable.

It must preserve the distinction:

`Person != Data Subject != Audience != Authority`

Exact identity representation remains open.

### Action draft

A typed but **non-executable** representation of model-derived intent that may still contain missing or unresolved material details.

A draft is not an action proposal. It cannot be authorized or executed as-is. Ada-owned application logic must resolve required information and create a valid proposal explicitly.

### Action proposal

A typed, complete description of a consequential operation proposed for authorization/execution.

A proposal is not permission and is not evidence of execution.

### Grant / Guard decision

The deterministic decision produced by Ada Guard for a concrete action proposal and context.

Learning, model confidence, or prior successful actions must not expand a grant.

### Operation identity and action state

Every consequential operation receives a stable Ada operation ID before provider execution.

The ledger must be able to represent at least:

`proposed -> authorized -> executing -> committed`

and terminal/exception states such as:

`denied | failed | ambiguous`

An ambiguous provider outcome must be reconciled before retry.

### Authoritative memory

Long-lived user memory remains external, readable/editable without the agent runtime, and independent from conversation history, checkpoints, indexes, and action records.

## 4. Ports required for the first vertical slice

Only the ports needed for the first slice are defined now.

### AgentRuntimePort

Responsibility:

- accept permitted context plus a user request;
- return a normal answer and/or typed action proposals;
- support local model execution;
- expose no privileged provider credentials to model output;
- carry no authorization semantics.

Initial implementation: PydanticAI adapter.

### AdaGuard

Responsibility:

- evaluate a concrete action proposal against explicit Ada grants and current actor/audience context;
- fail closed when required context or authority is missing;
- return a deterministic allow/deny decision plus reason.

AdaGuard is Ada core, not a third-party port.

### ActionLedger

Responsibility:

- allocate stable operation IDs;
- persist action state before and after provider calls;
- support reconciliation after crashes or uncertain responses;
- prevent duplicate consequential side effects when a stable provider/idempotency mechanism exists.

The storage technology is not selected here.

### CalendarPort

Initial narrow responsibility:

- read events required for conflict checks;
- create one event with an Ada operation ID / idempotency context where the provider allows it;
- retrieve/reconcile the result of an attempted create.

Update, cancellation, recurrence, invite handling, and arbitrary deletion are deliberately deferred until a scenario requires them.

### TravelTimePort

Initial narrow responsibility:

- return an approximate travel duration between two known locations;
- identify the source/type of estimate sufficiently for Ada to communicate uncertainty;
- work with configured/static estimates before any live-location capability is considered.

No location surveillance is implied.

### AuditEventPort

Responsibility:

- record privacy-conscious operational/security events needed to explain consequential behavior;
- avoid storing full prompts, private documents, secrets, or unnecessary message content by default.

This may initially be implemented together with the Action Ledger if that remains simpler. It is a semantic boundary, not necessarily a separate subsystem.

### PersonalityMemoryPort

Responsibility:

- load the active user-controlled personality profile;
- persist the initial distribution seed only when personality Memory is empty;
- preserve existing personality across Ada upgrades/reinstalls;
- support attributable personality changes without granting authority.

This is deliberately a **narrow semantic slice of Memory**, introduced because local chat now needs a concrete personality lifecycle. It does not select the general Memory backend or retrieval/index architecture.

## 5. Boundaries intentionally deferred

Do not define broad abstractions before the relevant slice needs them.

Deferred ports include:

- MessageChannelPort for email and later channels;
- SchedulerPort for requested/background work;
- general authoritative MemoryPort and retrieval/index contracts;
- UI/application transport;
- remote/cloud model broker;
- speech/perception;
- general computer control.

Their architectural boundaries are known from ADR-0002, but their APIs should be designed from concrete scenarios rather than speculation.

## 6. First vertical slice

The first implementation slice combines representative scenarios S1 and S2 without committing to a production calendar provider or UI.

### Input

A synthetic local request asks Ada to create an ordinary calendar event for which an explicit test grant exists.

A second existing synthetic event plus a configured travel estimate creates a conflict.

### Required path

```text
synthetic/local input
  -> PydanticAI runtime adapter
  -> typed CreateCalendarEvent proposal
  -> AdaGuard
  -> ActionLedger
  -> CalendarPort test adapter
  -> committed result
  -> conflict check using TravelTimePort
  -> concise result to caller
```

### Acceptance criteria

- the model cannot bypass AdaGuard;
- denied actions produce zero provider writes;
- an allowed action produces exactly one provider effect;
- a crash/retry does not duplicate that effect;
- the reported result distinguishes proposed, denied, failed, ambiguous, and committed states;
- the conflict is detected using travel time;
- no PydanticAI type appears in the Ada domain contracts;
- replacing the runtime test adapter must not require changing Guard, Ledger, CalendarPort, or conflict-domain logic.

## 7. Reuse / adapt / build rule

For every subsequent capability:

1. define the Ada behavior from a representative scenario;
2. identify the smallest stable Ada-owned boundary;
3. evaluate existing components;
4. choose **reuse**, **adapt**, or **build** based on lifetime effort, security/privacy fit, license, maintenance, and replaceability;
5. keep the third-party implementation behind the Ada boundary;
6. add a new ADR only when the choice materially affects architecture or long-term coupling.

OpenJarvis may be evaluated component-by-component under this rule.

## 8. Still-open cross-cutting decisions

This document does not resolve:

- final process topology or IPC;
- programming language/package layout;
- UI technology;
- production calendar/email providers;
- memory representation/backend;
- scheduler implementation;
- packaging, signing, startup, background service, or updates;
- quantitative CPU/RAM/storage/energy budgets;
- cross-platform/server deployment.

Those decisions should be made only when the first working slice requires them.
