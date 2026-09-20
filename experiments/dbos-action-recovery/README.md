# DBOS Action Recovery Probe

**Status:** disposable architecture experiment.

This probe compares DBOS 3.0.0 with Ada's custom SQLite Action Ledger control.

## Question

Can DBOS remove most of Ada's custom durable-execution/recovery machinery while preserving Ada-owned operation identity and provider/business outcome semantics?

## Why DBOS

Current DBOS Python 3.0.0:

- is MIT licensed;
- supports Python 3.14;
- runs in-process as a library;
- can use SQLite as its system database;
- automatically recovers pending workflows;
- uses stable workflow IDs as workflow-invocation idempotency keys;
- has a native PydanticAI integration.

## Critical crash window

The probe deliberately kills the process inside a DBOS step **after the fake external provider has committed but before DBOS can checkpoint the step result**.

Two provider modes are tested:

### Reconciled provider

The provider can find an existing effect by Ada operation ID.

Expected:

```text
attempt 1
  provider commits
  process dies
restart
DBOS re-executes uncheckpointed step
  provider reconciliation finds existing effect
workflow completes
```

Expected evidence:

- provider step attempts: 2
- provider effects: 1

### Unsafe provider

The provider has neither idempotency nor reconciliation.

Expected evidence:

- provider step attempts: 2
- provider effects: 2

This negative case is intentional. It verifies that DBOS, like other durable-execution systems, cannot manufacture exactly-once semantics for an arbitrary external API.

## Workflow identity

Ada operation ID is used as the DBOS workflow ID.

After successful completion, invoking the same workflow ID again should return the recorded result without re-executing the provider step.

## Run

```bash
uv sync --python 3.14
uv run --python 3.14 python -m unittest -v test_dbos_recovery.py
```

No PydanticAI model/API access is required.

## Decision relevance

DBOS is attractive only if Ada can keep the boundary:

```text
Ada operation / outcome semantics
        |
private durable-execution adapter
        |
DBOS
```

DBOS workflow status is not automatically equivalent to Ada provider/business outcome truth.
