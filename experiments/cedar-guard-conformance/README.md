# Cedar Guard conformance probe

**Status:** disposable architecture experiment.

This probe tests whether Ada can use the real Cedar authorization engine through the community-maintained `cedarpy` Python binding while preserving Ada-owned request/decision semantics.

## Why cedarpy first

`cedarpy`:

- wraps the Rust `cedar-policy` engine using PyO3/maturin;
- currently tracks Cedar Policy 4.12.0;
- publishes Linux aarch64 + Python 3.14 wheels;
- publishes macOS aarch64 + Python 3.14 wheels;
- supports authorization, diagnostics, reusable PolicySet/Schema handles, and schema validation;
- is Apache-2.0;
- is community maintained rather than officially supported by the Cedar team.

This lets Ada test Cedar without:

- writing a Rust bridge;
- adding a policy sidecar/service;
- adding an IPC/network failure mode.

A local service remains a later isolation option behind the same AdaGuard boundary.

## Architecture under test

```text
Ada AuthorizationRequest
        |
thin CedarGuard adapter
        |
cedarpy (Python/PyO3)
        |
official cedar-policy Rust engine
        |
Ada GuardDecision
```

The adapter owns only mapping and Ada's stricter fail-closed behavior.

## Install / run

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest -v conformance_test.py
```

## Conformance cases

The probe covers the same MVP cases as the custom-evaluator control, plus Cedar configuration validation:

1. explicit calendar grant;
2. default deny;
3. explicit forbid overrides permit;
4. direct authenticated one-off approval;
5. forwarded content cannot approve;
6. model-originated content cannot approve;
7. expiry/revocation removes authority;
8. busy-time disclosure vs private details;
9. malformed request fails closed;
10. invalid Cedar policy/schema combination is rejected before use.

## Important boundary

Cedar is the authorization engine, not the whole permission system.

Ada still owns:

- authentication claims;
- direct/forwarded provenance extraction;
- grant creation and storage;
- grant revocation lifecycle;
- policy version/deployment;
- Action Ledger;
- provider result truth;
- the stable AdaGuard API.

## Contribution path

If cedarpy proves suitable but lacks a small capability Ada needs, prefer proposing/contributing the change upstream rather than maintaining an Ada-specific fork.

Any upstream contribution must remain optional to Ada until released/pinned and independently reviewed.
