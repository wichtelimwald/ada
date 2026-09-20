# Results — DBOS Action Recovery Probe

**Status:** Prepared against current stable DBOS 3.0.0; target execution pending.

## Dependency

- DBOS: 3.0.0 stable
- license: MIT
- Python: >=3.10, Python 3.14 supported
- local system database: SQLite

## Pass criteria

The experiment succeeds as architecture evidence if it shows all of these explicitly:

1. DBOS survives the same hard-crash/restart scenario as the custom control.
2. The uncheckpointed external step is re-executed after recovery.
3. Provider reconciliation/idempotency keeps the reconciled provider at exactly one real effect.
4. An unreconcilable provider demonstrates that DBOS alone does not guarantee exactly-one external effect.
5. Reusing the completed DBOS workflow ID does not execute the provider step again.
6. Ada can keep provider outcome / business outcome semantics outside DBOS-native types.

A successful result does not automatically select DBOS; it enables evidence-based rescoring against the custom control, Restate, and Temporal.
