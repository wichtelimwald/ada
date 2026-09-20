# Results — Action Ledger crash/recovery probe

**Status:** Passed as a control implementation.

## Execution

The standard-library-only prototype was executed independently on Linux.

Result:

```text
5/5 PASS
```

## Passed cases

1. provider commits, then the process dies via `os._exit()` before Ada records `committed`;
2. restart sees the durable operation still in `executing`;
3. recovery reconciles the provider rather than repeating the write;
4. the operation becomes `committed` while provider effect count remains exactly one;
5. denied operation produces zero provider writes;
6. illegal state transitions are rejected;
7. compare-and-set transition prevents a second stale claim;
8. provider with no reconciliation support moves the operation to `ambiguous` and is not automatically retried.

## Interpretation

The explicit Ada state-machine + SQLite approach is technically viable.

It proves the required recovery contract can be implemented without a workflow framework.

It does **not** prove this should be the production choice. Mature durable-execution systems must be evaluated before accepting a custom implementation.

## Exactly-once boundary

The fake provider deliberately supports a stable Ada operation ID and reconciliation.

The test therefore validates:

> provider idempotency/reconciliation + durable Ada operation state can prevent duplicate effects across a hard crash.

It does not claim that SQLite, or any workflow engine, can manufacture exactly-once semantics for an arbitrary external provider that lacks idempotency/reconciliation.
