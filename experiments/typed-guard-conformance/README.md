# Typed Guard conformance probe

**Status:** disposable architecture experiment.

This probe tests whether Ada's confirmed MVP permission semantics can remain small enough for an Ada-owned typed evaluator without inventing a general policy language.

## Deliberate constraints

The evaluator has:

- typed request fields;
- typed allow/deny rules;
- exact/set-based selectors only;
- validity windows;
- revocation;
- minimum channel/authentication assurance;
- deterministic deny-overrides;
- deterministic reason codes and matched rule IDs.

It does **not** have:

- arbitrary expressions;
- callbacks;
- Python predicates in policy data;
- inheritance;
- role graphs;
- general boolean policy syntax;
- model-written grants.

If the MVP cases cannot be expressed cleanly under these constraints, the experiment fails and Cedar should be prototyped instead.

## Run

```bash
python -m unittest -v conformance_test.py
```

No third-party dependency is required.

## Cases

1. recognized calendar create with explicit grant;
2. default deny without grant;
3. explicit deny overrides broad allow;
4. direct authenticated one-off approval;
5. forwarded instruction cannot approve;
6. model-supplied "permission" cannot approve;
7. revoked/expired grants stop authorizing;
8. private event can contribute busy time while detail disclosure to family is denied;
9. malformed authorization request fails closed.
