# Context-awareness characterization harness

This directory is **research evidence**, not Ada product runtime code.

It compares candidate temporal resolvers against a fixed trusted context before ADR-0007 selects a dependency or execution policy.

## Fixed context

- reference: 2026-09-20T12:00:00+02:00
- timezone: Europe/Berlin
- locale: de-DE
- date order: DMY
- incomplete-date bias: future

The expressions are intentionally short temporal fragments. The target Ada architecture expects the LLM to perform semantic extraction first; the temporal resolver should not be responsible for understanding an unrestricted full user request.

## Initial candidates

- dateparser 1.4.3
- Acreom quickadd, pinned to commit 0b3bfc26a7347a80821e86eb3838556a7adc2a30

They are installed into **separate temporary virtual environments**. Neither is added to Ada's product dependencies.

Keeping them isolated is intentional: installation or runtime failure of one candidate must not prevent evidence collection for the other. A parser returning no result is **not** treated as proof that the resolver is operationally unavailable; runtime health is a separate future signal.

## Run on the target Mac

From the repository root, with Ada's Python 3.14 environment already available:

~~~sh
sh research/context_awareness/run.sh
~~~

The script currently:

1. creates isolated environments for dateparser, normal Quickadd, and Quickadd with the scorer disabled;
2. installs the top-level research candidates independently;
3. runs the shared characterization corpus;
4. exports the pinned Quickadd scorer to primitive JSON when the normal Quickadd run succeeds;
5. creates a fourth isolated Quickadd environment that loads that JSON scorer without runtime pickle deserialization;
6. prints all available raw JSON results;
7. prints pairwise semantic comparisons for dateparser vs Quickadd, Quickadd vs DummyScorer, and Quickadd vs JSON-backed scorer when the relevant runs succeed.

The requirements files pin the **top-level candidates only**. Transitive dependencies are still resolved by pip at run time. Therefore these research runs do not by themselves close ADR-0007's reproducible-dependency hard gate.

No GitHub Actions are used.

## Comparison states

For each case, the comparison reports one of:

- agreement — both resolvers produced the same normalized meaning;
- interpretation_conflict — both produced a result, but meanings differ;
- single_resolver_result — one resolver produced a result while the other was healthy enough to run but produced no result;
- input_error — at least one resolver raised an input-specific error while processing the expression;
- unresolved — neither produced a result and neither reported an input error.

These comparison states do not represent operational health. In particular, `single_resolver_result` must not be interpreted as degraded availability.

These states are evidence, not final Ada execution policy.

In particular:

- agreement increases interpretation confidence but does **not** prove truth;
- disagreement is at least a correctness/safety signal and may become security-relevant if crafted input can create parser differential confusion across a consequential boundary;
- runtime redundancy may improve availability, but operational health must be established independently of the current expression before fallback is allowed;
- license/privacy/platform hard gates remain mandatory regardless of characterization score.

## Case groups

- core — required behavior for the first temporal-resolution slice;
- policy — deliberately ambiguous cases where the benchmark records behavior before Ada chooses a policy;
- safety — DST and other cases where a syntactically valid wall time may not denote one unambiguous instant;
- extended — useful capabilities that are not required for the first MVP slice.

## Scoring rule

Only cases with an explicit expected value contribute an automatic pass/fail signal. Policy cases are recorded without silently declaring one library behavior correct.

The final ADR decision matrix should combine:

1. hard gates (license, local/offline fit, security/privacy constraints, supported deployment path);
2. measured characterization behavior;
3. runtime/packaging fit;
4. integration/provenance quality;
5. maintenance/release health;
6. operational complexity;
7. redundancy/availability value.

A failed hard gate excludes a candidate; it cannot be compensated by a high weighted score.


## Diagnostic Run 2

After Run 1, two targeted diagnostics were added:

1. **dateparser metadata** — the adapter now uses `DateDataParser` and records parser period/granularity plus locale, with given language order enforced. This helps distinguish a plausible datetime from a parser type mismatch.
2. **quickadd-safe** — a third isolated environment patches only Quickadd's default scorer initialization to use `DummyScorer` instead of loading the bundled pickled Naive Bayes model. This is research only; it tests whether the probabilistic scorer is needed for Ada's representative corpus.

The second comparison therefore answers a concrete hardening question:

- if `quickadd` and `quickadd-safe` stay semantically equivalent on the corpus, a no-pickle integration/fork becomes technically plausible;
- if behavior degrades materially, the scoring model is part of the functionality Ada would need to preserve through a safer serialization/loading design.

Re-run the same command:

~~~sh
sh research/context_awareness/run.sh
~~~


## Optional Duckling benchmark

After Run 3 demonstrated a safe JSON-backed Quickadd path, the remaining major trade-off is maintenance burden versus adopting a heavier independently maintained specialist.

An optional Duckling benchmark is therefore provided:

~~~sh
sh research/context_awareness/run_duckling.sh
~~~

The script:

1. requires a locally available Docker daemon;
2. clones the upstream Facebook Duckling repository;
3. checks out pinned commit `59a13ff87b1aa8be6b93d387244f8636b26185c5`;
4. builds the **upstream Dockerfile locally** instead of trusting a third-party image;
5. binds the service only to `127.0.0.1:18000`;
6. runs the same characterization corpus with explicit reference time, `de_DE`, and `Europe/Berlin`;
7. removes the container and temporary source checkout afterward.

A build failure is itself useful operational evidence. The current upstream Dockerfile still uses a Haskell 8 / Debian Buster build/runtime base, which may impose significant maintenance cost even if Duckling's temporal semantics are strong.

This benchmark remains research-only and does not add Duckling to Ada's runtime dependencies.
