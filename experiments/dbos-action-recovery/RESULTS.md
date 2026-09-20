# Results — DBOS Action Recovery Probe

**Status:** Passed on target Mac with current stable DBOS 3.0.0.

## Target environment

- macOS host / Apple Silicon
- Python: CPython 3.14.6
- DBOS: 3.0.0
- local durable system database: SQLite
- dependencies resolved/installed successfully with uv

## Result

```text
Ran 3 tests in 21.110s

OK
```

## Case 1 — hard crash + reconcilable provider

Passed.

The process died after the fake external provider committed but before DBOS could checkpoint the step result.

After restart:

- DBOS recovered the workflow;
- the uncheckpointed step executed again;
- provider reconciliation by Ada operation ID found the existing effect;
- provider step attempts = 2;
- real provider effects = **1**;
- the workflow completed successfully.

### Interpretation

DBOS provides the durable execution/recovery substrate. Ada/provider idempotency or reconciliation remains responsible for preventing duplicate external effects in the crash window.

## Case 2 — hard crash + unreconcilable provider

Passed as a negative boundary test.

After restart:

- DBOS recovered the workflow;
- the uncheckpointed external step executed again;
- because the provider offered neither idempotency nor reconciliation, a second external effect occurred;
- provider step attempts = 2;
- real provider effects = **2**.

### Interpretation

This confirms the documented DBOS boundary: external steps are at-least-once around an uncheckpointed crash window.

Therefore DBOS **cannot replace Ada's provider capability/outcome semantics**.

For a provider without idempotency/reconciliation, Ada must not expose the raw automatically retried external step as a safe consequential action. The Ada durable-action adapter must stop/recover as `ambiguous` rather than blindly repeating the provider effect.

## Case 3 — stable workflow ID after completion

Passed.

Ada operation ID was used as the DBOS workflow ID.

After successful completion, invoking the same workflow ID again returned the durable result without another provider attempt.

### Interpretation

Ada's stable operation ID maps naturally to DBOS workflow identity/idempotency.

## What DBOS can replace

DBOS can plausibly replace substantial custom infrastructure for:

- durable workflow checkpoints;
- workflow restart/recovery;
- stable workflow invocation identity;
- durable waiting/sleeping;
- long-running coordination;
- signals/events/queues;
- durable PydanticAI execution integration.

## What remains Ada-owned

Ada still needs a small semantic Action Ledger boundary for:

- stable Ada operation ID;
- Guard decision linkage;
- provider capability classification;
- provider reference;
- provider outcome;
- business outcome;
- `ambiguous` semantics;
- reconcile-before-retry rule;
- minimal privacy-safe audit view.

DBOS workflow status is evidence about **execution**, not automatically the truth about a real-world business outcome.

## Privacy implication

DBOS persists workflow inputs/outputs and step outputs in its system database.

A production integration must pass minimal operation envelopes/references rather than raw emails, prompts, private documents, secrets, or authoritative Memory.

## Conclusion

DBOS 3.0.0 is technically viable on Ada's target platform and removes a substantial amount of custom durable-execution/recovery machinery.

It does **not** eliminate Ada's semantic Action Ledger or provider reconciliation boundary.

The likely architecture, if selected, is:

```text
Ada Action Ledger semantics
        |
Ada durable-action adapter
        |
DBOS workflow / durable execution
        |
provider adapter
        |
external system
```

The custom SQLite state machine remains the control/fallback, not automatically the preferred production implementation.
