# Context-awareness characterization — Run 3

- **Date:** 2026-09-20
- **Target:** MacBook Air M1 / Python 3.14
- **Purpose:** verify whether Quickadd's trained scorer can be loaded from a transparent primitive JSON representation without changing parser semantics

## Result

The JSON-backed scorer reproduced the normal Quickadd result on **all 15 characterization cases**:

- quickadd vs quickadd-json: **15 agreements**
- interpretation conflicts: **0**
- degraded-single-resolver cases: **0**

For the 11 cases with explicit expected results:

- **quickadd:** 11/11
- **quickadd-json:** 11/11

This includes the cases where DummyScorer failed:

- Friday interval;
- mixed German/English date-time;
- DST gap input retaining 02:30;
- DST fold input retaining 02:30.

## Security conclusion

The behaviorally important Quickadd scoring model does **not** require Python pickle as its runtime representation.

Its relevant state was exported to a versioned primitive JSON structure containing:

- n-gram range;
- vocabulary;
- alpha;
- class priors;
- negative and positive log-likelihood arrays.

A fresh Quickadd environment reconstructed the same CTParsePipeline from JSON and produced semantically identical output for the complete current characterization corpus.

Therefore Ada should **not** accept Quickadd's upstream import-time `pickle.load()` path in production.

A viable integration path exists:

1. pin a reviewed Quickadd source revision;
2. use a transparent, versioned JSON model artifact;
3. load and validate that artifact with Ada-owned safe code;
4. prevent the upstream default pickle loader from running;
5. verify JSON artifact integrity/hash and schema;
6. retain characterization/regression tests against upstream semantics.

## Remaining hardening question

The research harness obtains the JSON model by importing the pinned upstream package once in an isolated conversion environment. That conversion step still exercises upstream pickle deserialization.

This is acceptable as research evidence, but should **not** be the long-term Ada build/release trust model.

Before production adoption, choose one reproducible source-of-truth strategy:

- generate the model deterministically from reviewed training corpus/code;
- or review and convert one pinned upstream model once, commit the resulting transparent JSON artifact plus provenance/hash, and never require pickle during normal Ada build/runtime;
- preferably contribute/maintain the safe model-loading change upstream or in a minimal auditable fork.

## Architectural implication

Run 3 materially strengthens the candidate architecture:

- **Primary temporal semantics:** Quickadd/ctparse lineage with safe JSON scorer loading;
- **Independent shadow/fallback:** dateparser for characterized compatible classes;
- **Ada deterministic validation:** expected semantic kind, provenance, locale policy, zoneinfo wall-time validity;
- **Selective consensus:** only where both resolvers have demonstrated comparable semantics;
- **degraded operation:** one resolver may continue for explicitly characterized low-risk classes.

This is not yet final acceptance because maintenance/fork strategy and the independent benchmark question still remain.

## Next decision question

The remaining substantive decision is whether Quickadd's stronger semantics plus a small safe-loader maintenance surface is preferable to introducing a heavier but independently maintained specialist such as Duckling.

ADR-0007 should not be marked Accepted until that trade-off is explicitly documented.
