# Action Ledger crash/recovery probe

**Status:** disposable architecture experiment.

This tests the narrowest recovery contract needed by Ada's first consequential-action slice.

## What it proves

The critical path is:

1. Ada records an authorized operation.
2. Ada durably moves it to `executing`.
3. the provider commits the external effect using Ada's stable operation ID;
4. the process dies via `os._exit()` before Ada records `committed`;
5. a fresh process finds the operation still in `executing`;
6. recovery reconciles the provider;
7. the existing provider effect is recorded as `committed`;
8. provider effect count remains exactly one.

Additional cases:

- denied operation -> zero provider writes;
- illegal state transitions rejected;
- compare-and-set transition prevents double claiming the same state;
- unknown provider outcome with no reconciliation support -> `ambiguous`, no automatic retry.

## Run

```bash
python3 -m unittest -v test_recovery.py
```

No third-party dependency is required.

## Important limitation

The fake provider intentionally stores effects in a separate SQLite database and makes `operation_id` unique. It represents a provider with stable idempotency/reconciliation support.

The experiment does **not** claim Ada can manufacture exactly-once behavior for a provider that offers neither capability.
