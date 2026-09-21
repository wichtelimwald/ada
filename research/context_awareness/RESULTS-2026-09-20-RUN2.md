# Context-awareness characterization — Run 2

- **Date:** 2026-09-20
- **Target:** MacBook Air M1 / Python 3.14
- **Purpose:** characterize dateparser type metadata and Quickadd behavior without import-time pickle model loading

## Summary

All three environments installed and executed:

- dateparser 1.4.3
- quickadd 0.6.5 with bundled Naive Bayes scorer
- quickadd-safe 0.6.5 with the default scorer replaced by DummyScorer before import

For the 11 cases with explicit expected results:

- **quickadd:** 11/11
- **dateparser:** 8/11
- **quickadd-safe:** 7/11

Quickadd vs quickadd-safe:

- agreement: 10
- interpretation_conflict: 5

The bundled scoring model therefore materially affects result selection. Removing pickle loading by simply falling back to DummyScorer is **not** behaviorally equivalent.

## dateparser metadata finding

Using DateDataParser exposes parser period/granularity.

This helps detect some semantic mismatches:

- `21.10.` is resolved as 21:10 on the reference day and explicitly labeled `period=time`. If the typed LLM extraction says the field is a date expression, Ada can reject this as a type mismatch rather than accepting a plausible wrong value.
- `Freitag 9-11` is labeled `period=day` and returned as a single point although Ada expects an interval.

However metadata does **not** rescue all failures:

- `morgen um 16 Uhr` is labeled `period=day` and resolves to 12:00, losing the requested time.

This makes dateparser more useful as a typed secondary validator than as the sole general appointment resolver.

## quickadd-safe failures

Replacing the bundled Naive Bayes scorer with DummyScorer preserved many simple cases, including:

- `21.10.`
- `3.1.`
- `morgen um 16 Uhr`
- explicit full/past dates
- simple weekday
- relative duration

But it failed 4/11 explicit expected cases:

1. `Freitag 9-11` became an underspecified month-like Time instead of an interval.
2. `morgen 4pm` lost the time and returned midnight.
3. DST-gap input lost 02:30 and returned midnight.
4. DST-fold input lost 02:30 and returned midnight.

It also changed the recurring-expression interpretation.

Conclusion: the probabilistic scorer is materially involved in choosing the correct parse for several relevant expression classes.

## Security implication

Quickadd's current bundled scorer remains behaviorally valuable but is loaded through Python pickle during normal import.

Therefore:

- simply disabling the scorer does not satisfy Ada's quality requirements;
- accepting the current import-time pickle path without further hardening would leave a material supply-chain / unsafe-deserialization concern;
- the next investigation should determine whether the scorer can be represented and loaded through a safe transparent format, or reconstructed from source/corpus deterministically.

## Redundancy implication

Run 2 strengthens the case for **heterogeneous primary + shadow** rather than homogeneous dual consensus:

- quickadd is stronger on appointment semantics;
- dateparser is independently maintained and can corroborate many simple date/time cases;
- typed expected semantic kind can make dateparser disagreement more informative;
- the two implementations fail differently, which is valuable for shadow validation and availability.

Do not count quickadd-safe as an independent redundant resolver. It shares Quickadd's parser/rule base and merely changes ranking behavior.

## Next step

Before accepting ADR-0007:

1. inspect Quickadd's scorer/model representation and determine whether a safe serialization/reconstruction path is practical;
2. if not practical, benchmark Duckling as the next independent specialist candidate;
3. keep dateparser as a likely lightweight shadow/fallback candidate rather than the primary appointment parser;
4. only then finalize the hard-gate and weighted decision matrix.


## Terminology note

This file preserves the output/terminology of the harness version used for this historical run. The later ADR and harness distinguish a healthy parser returning no result from true operational unavailability. New comparisons use `single_resolver_result` for the former and preserve input-specific failures as `input_error`; neither should be interpreted as automatic degraded-mode authorization.
