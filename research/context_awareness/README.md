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

Keeping them isolated is intentional: installation or runtime failure of one candidate must not prevent evidence collection for the other. This also lets the benchmark observe a potential future degraded-single-resolver availability mode.

## Run on the target Mac

From the repository root, with Ada's Python 3.14 environment already available:

~~~sh
sh research/context_awareness/run.sh
~~~

The script:

1. creates two disposable virtual environments;
2. installs each pinned research dependency independently;
3. runs the same characterization corpus against both;
4. prints each raw JSON result;
5. if both are available, prints a semantic comparison.

No GitHub Actions are used.

## Comparison states

For each case, the comparison reports one of:

- agreement — both resolvers produced the same normalized meaning;
- interpretation_conflict — both produced a result, but meanings differ;
- degraded_single_resolver — one produced a result and the other did not;
- unresolved — neither produced a result.

These states are evidence, not final Ada execution policy.

In particular:

- agreement increases interpretation confidence but does **not** prove truth;
- disagreement is at least a correctness/safety signal and may become security-relevant if crafted input can create parser differential confusion across a consequential boundary;
- single-resolver operation may improve availability, but Ada must decide which classes of derived values are safe to accept without corroboration;
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
