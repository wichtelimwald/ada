# ADR-0007: Context-aware natural-language interpretation

- **Status:** Proposed
- **Date:** 2026-09-20

## Context

Ada should understand ordinary human phrasing without requiring users to learn a hidden command grammar.

For example, on 2026-09-20 in Europe/Berlin:

- "Zahnarzt am 21.10. um 16 Uhr" should not require the user to restate the obvious year merely because the model output schema uses an ISO date.
- "morgen um 16 Uhr" should be resolvable from trusted runtime time context.
- "in meinen Kalender" may eventually resolve through an explicit user/default-calendar preference.
- multi-turn clarification such as "morgen um 16 Uhr" after an incomplete calendar request must remain linked to the pending typed action state.

At the same time, Ada's security invariants remain unchanged:

- model interpretation is not authority;
- context, memory, habits, or learned preferences must not grant permissions;
- derived values must remain distinguishable from explicit user input;
- consequential action truth comes from Ada application/provider outcomes, never from free model text.

PR #23 exposed the danger of trying to make natural-language intent recognition itself a deterministic security boundary. Finite verb/keyword lists are both bypassable and hostile to natural interaction. This ADR therefore separates four concerns:

1. semantic interpretation of free language;
2. injection of trusted runtime/user context;
3. deterministic normalization and provenance of context-dependent values;
4. authorization/execution.

## Requirements

The approach must:

- preserve natural German and English interaction;
- work with Python 3.14 and the current PydanticAI adapter;
- remain local-first and replaceable;
- avoid a growing Ada-owned dictionary/regex grammar for general language;
- support partial and relative temporal expressions;
- support explicit reference time, timezone, and locale;
- eventually support known/default calendars and user-controlled preferences;
- preserve provenance for every derived material value;
- keep ambiguity visible rather than silently converting uncertain guesses into executable facts;
- remain independent of AdaGuard authority decisions;
- fit Ada's low-maintenance, reuse-first development model.

## Reuse patterns reviewed

### Mark LIV

Mark LIV injects current date/time into the model context at session start and explicitly tells the model to use it when calculating reminder times. Its reminder tool then expects canonical date/time parameters.

Useful pattern:

- trusted runtime context is supplied to the model;
- the model performs semantic interpretation;
- a structured tool boundary receives canonical arguments.

What Ada should not copy:

- treating model normalization alone as sufficient provenance/validation;
- coupling Ada's architecture to Mark LIV implementation details or licensing.

Reference:
- https://github.com/FatihMakes/Mark-LIV

### OpenJarvis

OpenJarvis has an explicit AgentContext, automatic memory context injection, and structured tool-calling agents. Relevant context is retrieved and prepended to the prompt with source attribution; tool calls are separated from final free text.

Useful pattern:

- context injection is a first-class pipeline concern;
- conversation, tools, memory results, and metadata are distinct runtime inputs;
- semantic routing/tool selection remains model-driven while execution stays structured.

References:
- https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/overview.md
- https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/agents.md
- https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/query-flow.md

### PydanticAI

PydanticAI already provides typed per-run dependencies through deps / RunContext. Dependencies can be consumed by dynamic instructions, tools, and output validators.

This is a strong fit for supplying Ada-owned trusted context without introducing a second context framework.

Reference:
- https://pydantic.dev/docs/ai/core-concepts/dependencies/

## Temporal normalization candidates

### dateparser

Current researched version: **1.4.3** (2026-09-03).

Relevant properties:

- BSD-3-Clause;
- Python 3.14 explicitly supported;
- pure-Python wheel;
- actively maintained;
- multilingual, including German;
- RELATIVE_BASE supplies a trusted reference datetime;
- PREFER_DATES_FROM can bias incomplete expressions toward future/past;
- timezone-aware parsing is supported;
- incomplete dates are explicitly supported.

Important limitation:

- the documentation warns that date extraction from arbitrary long text can produce false positives;
- Ada should therefore prefer model-extracted temporal expressions as parser input rather than asking search_dates() to understand the whole user request.

References:
- https://pypi.org/project/dateparser/
- https://dateparser.readthedocs.io/en/latest/
- https://dateparser.readthedocs.io/en/latest/settings.html

### quickadd / ctparse lineage

Acreom's quickadd is an actively maintained fork of the archived Comtravo ctparse project.

Relevant properties:

- MIT;
- Python implementation;
- specifically designed for natural-language temporal interpretation;
- German and English;
- explicit reference time;
- future-biased resolution of partial dates;
- intervals, durations, recurring expressions, subject extraction;
- the documented behavior explicitly treats e.g. "12.5." as the next 12 May relative to the reference time.

Concerns:

- packaging metadata still advertises old Python versions;
- installation documentation points to GitHub rather than a mature current PyPI release path;
- Python 3.14 compatibility is not documented;
- project maturity/maintenance surface is smaller than dateparser.

Reference:
- https://github.com/Acreom/quickadd

### Duckling

Relevant properties:

- mature temporal/entity parser;
- German locale support;
- explicit referenceTime, locale, and timezone context;
- BSD-style licensing in source;
- actively used and still maintained.

Concerns for Ada:

- Haskell runtime/build surface;
- likely separate service/process or nontrivial embedding work;
- materially higher operational and packaging cost than a Python library.

Keep as a benchmark, not the default first integration candidate.

Reference:
- https://github.com/facebook/duckling

### Microsoft Recognizers-Text

Relevant properties:

- MIT;
- German DateTime support;
- explicit reference datetime;
- mature cross-language date/time extraction and resolution.

Concerns for Ada:

- Python packaging is stale: the published recognizers-text-suite package is still an alpha release from 2019 and advertises Python 3.6-era metadata;
- repository development continues, but the Python distribution story is weak for a Python-3.14 project.

Keep as a benchmark unless the packaging situation changes.

References:
- https://github.com/microsoft/Recognizers-Text
- https://pypi.org/project/recognizers-text-suite/

### HeidelTime

Relevant properties:

- strong multilingual temporal tagging and German support;
- TIMEX3 normalization.

Rejected for this Ada slice because:

- Java/UIMA-oriented integration;
- GPL-3.0;
- optimized for document temporal tagging rather than lightweight interactive assistant input.

Reference:
- https://github.com/HeidelTime/heideltime

## Decision direction

### 1. Do not build an Ada natural-language grammar

Ada will **not** maintain a general regex/keyword dictionary to decide what users mean.

The LLM remains responsible for semantic interpretation into typed intent/draft structures.

Deterministic code validates, normalizes, authorizes, and executes those structures.

### 2. Reuse PydanticAI for trusted run context

Introduce an Ada-owned, framework-neutral context value, provisionally:

~~~
InterpretationContext
  now
  timezone
  locale
~~~

The PydanticAI adapter supplies this through typed deps / RunContext.

The Ada type remains independent of PydanticAI so another runtime can provide the same information later.

### 3. Separate semantic extraction from deterministic normalization

The desired flow is:

~~~
user natural language
        |
        v
LLM semantic extraction
  - typed intent
  - raw temporal expression(s)
  - raw target/calendar reference
        |
        v
deterministic resolver adapter
  - trusted reference time
  - timezone / locale
  - explicit resolution policy
        |
        v
resolved draft + provenance
        |
        v
Ada validation
        |
        v
Proposal -> AdaGuard -> durable execution
~~~

The temporal resolver should receive focused temporal expressions rather than unrestricted full user text where possible.

### 4. Add provenance as an Ada semantic, not a parser feature

A resolved material field must distinguish how its value was derived.

For this ADR the initial derivation kinds are deliberately limited to:

- explicit — directly and deterministically corroborated from the source;
- context_derived — derived from trusted runtime context plus an explicit resolution policy;
- defaulted — filled from an explicit configured default.

Memory-derived values are intentionally deferred to the later Memory architecture decision.

Example:

~~~
raw:       "21.10."
resolved:  2026-10-21
derivation:
  kind: context_derived
  basis:
    reference_date: 2026-09-20
    timezone: Europe/Berlin
    resolution_policy: temporal-defaults/v1
~~~

Value derivation explains why a value is present. It does not grant authority.

### 5. Put temporal parsing behind an Ada port

Do not expose one library's result model through Ada core.

A future implementation should define a small Ada-owned TemporalResolverPort (name provisional) so that dateparser, quickadd, Duckling, or another implementation can be characterized or replaced without changing action semantics.

### 6. Do not adopt a temporal library until characterization passes

Quickadd/ctparse semantics with a safe JSON-backed scorer is now the **preferred primary candidate**, subject to closing the conditional hard gate with a reproducible no-pickle artifact/loader strategy.

dateparser is the preferred **independent shadow/fallback candidate** for characterized compatible classes.

Duckling remains a future/reference benchmark but is excluded from the initial resolver path on deployment/maintenance grounds. Microsoft Recognizers-Text remains deferred.

## Decision gates and scoring

### Hard gates

Hard gates are evaluated **before** any weighted scoring.

A failed gate excludes a candidate; it cannot be compensated by a high score elsewhere.

| Gate | Rule |
| --- | --- |
| License compatibility | Must be compatible with Ada's licensing/distribution strategy; otherwise reject |
| Local/offline operation | Must not require a cloud service or external account for core parsing |
| Privacy/security fit | Must not introduce hidden external egress or weaken Ada's authority boundaries |
| Supported deployment path | Must be practically runnable on Ada's supported target environments |
| Reproducible dependency path | Version/source must be pinnable and auditable |

Unknowns remain TBD until characterized; TBD is not a pass.


### Candidate hard-gate status after characterization

| Candidate | License | Local/offline | Privacy/security | Deployment path | Reproducible source | Gate result |
| --- | --- | --- | --- | --- | --- | --- |
| dateparser 1.4.3 | PASS — BSD-3-Clause | PASS | PASS | PASS — Python 3.14 target Mac | **CONDITIONAL** — top-level release pinned, transitive graph not yet locked | **CONDITIONAL** |
| Quickadd 0.6.5 + safe JSON scorer | PASS — MIT | PASS | **CONDITIONAL PASS** — no runtime pickle; production artifact path still to formalize | PASS — Python 3.14 target Mac; Linux validation remains | **CONDITIONAL** — source commit pinned, transitive graph + JSON artifact provenance not yet fully locked | **CONDITIONAL** |
| Duckling 59a13ff8 | PASS — BSD-3-Clause | PASS | PASS in reviewed design | **NOT DEMONSTRATED for Ada container path** — pinned upstream Dockerfile fails without modernization; native Haskell path exists upstream | PASS — pinned commit | **DEFERRED / NOT SELECTED** |
| Microsoft Recognizers-Text | PASS — MIT | PASS | PASS in reviewed design | TBD — stale Python distribution path | TBD | **DEFERRED** |
| HeidelTime | **FAIL for Ada's MIT distribution strategy** — GPL-3.0 | PASS | PASS in reviewed design | Java/UIMA burden | PASS | **EXCLUDED before scoring** |

A conditional gate is not equivalent to a pass. Before dependency adoption, Ada must capture a fully resolved dependency graph and, for Quickadd, define a reproducible no-pickle model artifact and loader strategy.


### Current scored candidates

The scores below are **provisional research scores**. Neither Python candidate has yet closed the reproducibility gate, and Quickadd additionally has a conditional safe-artifact integration gate.

| Criterion | Weight | dateparser | Quickadd + safe JSON |
| --- | ---: | ---: | ---: |
| Ada characterization behavior | 30% | 2 | 5 |
| Runtime / packaging fit | 15% | 5 | 3 |
| Integration and provenance quality | 15% | 3 | 4 |
| German/English and ambiguity handling | 10% | 3 | 5 |
| Maintenance and release health | 10% | 5 | 2 |
| Operational complexity | 10% | 5 | 4 |
| Availability / redundancy contribution | 10% | 4 | 4 |
| **Weighted score** | **100%** | **3.50 / 5.00** | **4.05 / 5.00** |

Interpretation:

- **dateparser** is the stronger maintenance/packaging choice but materially weaker on Ada's appointment-language corpus.
- **Quickadd + safe JSON scorer** is the stronger semantic fit and current primary candidate, but Ada would own a small hardened integration surface.
- **Duckling is not scored** because semantic characterization never ran: the pinned upstream container path failed before parsing, while a native/polyglot path would add the exact operational burden ADR-0003 deliberately avoids for the initial topology. This is a defer/not-select decision, not a claim that Duckling is impossible to run.

### Weighted decision matrix

Only candidates that pass all hard gates are eligible for a **final selection score**. Conditional candidates may carry clearly labeled provisional research scores so the trade-off remains visible while their gates are being closed.

| Criterion | Weight |
| --- | ---: |
| Ada characterization behavior | 30% |
| Runtime / packaging fit | 15% |
| Integration and provenance quality | 15% |
| German/English and ambiguity handling | 10% |
| Maintenance and release health | 10% |
| Operational complexity | 10% |
| Availability / redundancy contribution | 10% |
| **Total** | **100%** |

Scoring uses 1-5:

- **5** — strong fit with little or no Ada-specific compensation;
- **4** — good fit with small explicit policy/adaptation;
- **3** — usable but requires meaningful Ada-side handling;
- **2** — substantial maintenance, operational, or correctness burden;
- **1** — poor fit; extensive custom behavior would be required.

For the 30% characterization criterion, a candidate loses score when Ada would need to recreate temporal-language rules around it. A library that requires a growing Ada-owned parsing grammar is therefore penalized even if selected examples can be made to pass.

### Redundant resolution as a characterized option

Ada should not assume that every temporal value requires two parsers.

The characterization comparison records result states without inferring runtime health:

- **agreement** — both resolvers produce the same normalized semantic result;
- **interpretation_conflict** — both produce results but disagree semantically;
- **single_resolver_result** — only one resolver resolves the expression and neither reports an input error;
- **input_error** — at least one resolver raised an input-specific exception/error while processing the expression;
- **unresolved** — neither resolver resolves the expression and neither reports an input error.

Operational availability is a separate runtime signal and must not be inferred from a parser returning no result.

Agreement increases interpretation confidence but is not proof of truth.

Disagreement is at least a correctness/safety signal. It becomes security-relevant when crafted input can create parser-differential confusion across a consequential boundary.

The benchmark will inform which future runtime policy is justified:

1. **single primary** — one resolver is sufficient for the relevant class of input;
2. **primary + shadow** — one resolver is authoritative for interpretation while another continuously checks for disagreement and provides availability evidence;
3. **dual consensus** — selected context-derived material values require semantic agreement before automatic execution;
4. **degraded single-resolver mode** — if one implementation is unavailable, allow the other only for explicitly defined low-risk/unambiguous classes; otherwise ask for clarification.

This allows redundancy to improve both **interpretation safety** and **availability/replaceability** without making Ada depend on two parsers for every explicit date.
## Characterization suite required before acceptance

Use a fixed trusted context, initially:

~~~
reference: 2026-09-20T12:00:00+02:00
timezone:  Europe/Berlin
locale:    de-DE
~~~

At minimum characterize:

| Input / extracted expression | Property to verify |
| --- | --- |
| 21.10. | resolves to the next contextually appropriate 21 October |
| 3.1. | crosses the year boundary rather than forcing the current year |
| morgen um 16 Uhr | relative day + explicit time |
| in 30 Minuten | relative duration |
| Freitag | future weekday semantics |
| nächsten Dienstag | document library semantics; do not silently accept an Ada policy until ambiguity is understood |
| 21.10.2026 | explicit year is preserved exactly |
| explicit past date | must remain explicit past; must not silently roll forward |
| 21.10.26 | characterize two-digit-year behavior and require explicit Ada policy |
| 04/05 | locale-sensitive ambiguity must be deterministic/visible |
| Freitag 9-11 | interval extraction/resolution |
| recurring phrasing | characterize but do not make recurring events an MVP requirement |
| DST gap in Europe/Berlin | nonexistent local time must not silently become another time |
| DST fold in Europe/Berlin | ambiguous local time must remain visible/qualified |

Also characterize:

- output precision and missing-part metadata;
- input span/source attribution;
- timezone behavior;
- failure/ambiguity signaling;
- determinism across repeated runs;
- behavior with German/English mixed phrasing;
- thread safety;
- dependency footprint and installation on Python 3.14 / target Mac.

## Characterization evidence — Run 1

The first target-Mac run completed successfully with both initial candidates installed in isolated Python 3.14 environments.

For the 11 cases with an explicit expected result:

- **quickadd:** 11/11 matched expected;
- **dateparser:** 8/11 matched expected.

Across all 15 cases, semantic comparison produced:

- 10 agreements;
- 3 interpretation conflicts;
- 2 degraded-single-resolver cases;
- 0 cases unresolved by both.

Material conflicts:

| Expression | Expected | dateparser 1.4.3 | quickadd 0.6.5 |
| --- | --- | --- | --- |
| `21.10.` | 2026-10-21 | interpreted as 21:10 on reference day | correct |
| `morgen um 16 Uhr` | 2026-09-21 16:00 | 2026-09-21 12:00 | correct |
| `Freitag 9-11` | Friday 09:00-11:00 interval | 2026-11-09 point | correct interval |

These are not minor edge cases: the first two are representative Ada interaction patterns.

Run 1 also confirmed that quickadd installs and executes on Ada's target Python 3.14 Mac despite its stale packaging metadata. That removes one uncertainty but does not establish long-term maintenance fitness.

### Provisional hard-gate status

| Gate | dateparser | quickadd |
| --- | --- | --- |
| License compatibility | PASS — BSD-3-Clause | PASS — MIT |
| Local/offline operation | PASS | PASS |
| Privacy/security fit | PASS in current review | **CONDITIONAL PASS** — Run 3 proves a no-pickle JSON scorer path with identical characterized semantics; production integration strategy still required |
| Supported target deployment | PASS — documented Python 3.14 | PASS on target Mac by characterization; Linux still to retain as supported path |
| Reproducible dependency path | PASS — pinned release | PASS — pinned Git commit, but weaker distribution ergonomics |

Quickadd is not yet eligible for final selection until the safe JSON loader/source-artifact strategy is made reproducible and auditable; the feasibility itself is now demonstrated.

### Provisional weighted view

This is informative only; final scoring occurs after all hard gates pass.

| Criterion | Weight | dateparser | quickadd | Evidence note |
| --- | ---: | ---: | ---: | --- |
| Ada characterization behavior | 30% | 2 | 5 | dateparser missed 3/11 expected cases including two core interactions; quickadd hit 11/11 |
| Runtime / packaging fit | 15% | 5 | 3 | quickadd works on Python 3.14 but is Git-pinned with stale packaging metadata |
| Integration and provenance quality | 15% | 3 | 4 | quickadd exposes richer temporal types/spans; dateparser granularity metadata still to characterize |
| German/English and ambiguity handling | 10% | 3 | 5 | quickadd handled core German and mixed-language cases better in Run 1 |
| Maintenance and release health | 10% | 5 | 2 | dateparser is actively maintained; quickadd's last substantive code changes are materially older |
| Operational complexity | 10% | 5 | 4 | both are Python-local; quickadd adds bundled probabilistic model handling |
| Availability / redundancy contribution | 10% | 4 | 4 | each resolves cases the other may miss; policy still TBD |

Provisional weighted score **if all hard gates passed**:

- dateparser: **3.50 / 5.00**;
- quickadd: **4.05 / 5.00**.

At Run 1 this security gate was still TBD. Run 3 later demonstrated a behaviorally equivalent JSON-backed scorer; the remaining gate is the reproducible production artifact/loader strategy.

### Security / maintenance finding: quickadd model loading

Quickadd loads its bundled Naive Bayes scoring model through Python `pickle.load()` during normal module import. The dependency is pinned, so this is not equivalent to accepting arbitrary runtime input, but it is an unsafe-deserialization/supply-chain surface and the model artifact is opaque.

This matters particularly because dateparser 1.4.0 explicitly removed its own import-time pickle loading as a security hardening change.

Before quickadd can pass the security hard gate, characterize at least one of:

1. a safe non-pickle model/scorer path;
2. a minimal maintained patch/fork with safe serialization;
3. a documented integrity/hardening approach that is acceptable for Ada's threat model.

### Redundancy implication from Run 1

Strict dual consensus for every context-derived temporal value is **not** supported by the evidence. It would block normal phrases where quickadd is correct and dateparser is not.

The strongest strategy to investigate next is:

- quickadd-like semantics as the primary path if its security/maintenance gate can be satisfied;
- a second resolver as shadow/fallback for characterized compatible classes;
- typed expected temporal kind/granularity so a resolver returning `time` for an expected `date`, or `point` for an expected `interval`, fails safely rather than becoming a plausible wrong value;
- selective consensus only where both resolvers have demonstrated comparable semantics.

Detailed raw-result analysis is recorded in `research/context_awareness/RESULTS-2026-09-20.md`.

## Characterization evidence — Run 2

Run 2 tested two targeted questions:

1. whether dateparser exposes enough semantic metadata to fail safely on type mismatches;
2. whether Quickadd can preserve behavior without its bundled pickled scorer.

Results:

- dateparser remains **8/11** on explicit expected cases;
- Quickadd with its bundled scorer remains **11/11**;
- Quickadd with DummyScorer falls to **7/11**;
- Quickadd vs DummyScorer: **10 agreements / 5 interpretation conflicts**.

Dateparser metadata is useful but insufficient as a sole resolver:

- `21.10.` is explicitly reported as parser period `time`, allowing Ada to reject a date-vs-time mismatch;
- `morgen um 16 Uhr` still resolves incorrectly to 12:00 while reported only as `day`, so granularity metadata does not recover the lost time;
- interval semantics remain weak for the representative appointment case.

Quickadd's probabilistic scorer is materially involved in choosing correct parses for intervals, mixed-language time expressions, and full date-time cases. Simply disabling pickle loading and using DummyScorer is therefore not an acceptable production hardening strategy.

### Safe-model feasibility finding

Source inspection shows that Quickadd's trained scorer state consists only of primitive model data:

- n-gram range;
- string-to-integer vocabulary;
- alpha;
- two class-prior floats;
- negative/positive log-likelihood float arrays.

These values are directly representable in a transparent JSON schema. The model does **not** require an inherently pickle-specific runtime representation.

This creates a plausible hardening path: convert the trusted pinned upstream model once in a controlled research/build step, then load only primitive JSON at runtime. A new `quickadd-json` characterization backend has been added to test whether this preserves exact semantics without runtime `pickle.load()`.

At Run 2 the no-pickle equivalence was still unproven. Run 3 later demonstrated equivalent behavior with a JSON-backed scorer; this Run 2 statement is retained only as historical research context.

Detailed evidence is recorded in `research/context_awareness/RESULTS-2026-09-20-RUN2.md`.

## Characterization evidence — Run 3

Run 3 tested whether Quickadd's behaviorally important trained scorer can be represented and loaded safely without runtime pickle deserialization.

Result:

- **quickadd vs quickadd-json: 15/15 semantic agreement**;
- **quickadd-json: 11/11** on cases with explicit expected values;
- no interpretation conflicts between normal Quickadd and the JSON-backed scorer on the complete current corpus.

This demonstrates that Python pickle is **not required by the model semantics**. The scorer state can be represented transparently as primitive JSON and reconstructed into Quickadd's own CountVectorizer / MultinomialNaiveBayes / CTParsePipeline types without changing characterized behavior.

### Updated hard-gate interpretation

Quickadd's upstream runtime path still fails Ada's preferred security posture because it executes `pickle.load()` during normal import.

However, Run 3 demonstrates a technically viable safe integration path. The privacy/security hard gate therefore changes from **unresolved feasibility** to **conditional pass pending implementation strategy**:

- no pickle deserialization in Ada normal build/runtime;
- versioned validated JSON model schema;
- pinned reviewed Quickadd source revision;
- artifact provenance and integrity hash;
- regression/characterization equivalence against the selected upstream revision;
- explicit ownership of the minimal safe-loader patch/fork or upstream contribution.

The research conversion currently imports the pinned upstream artifact once and is therefore evidence only; it must not become the production trust chain.

### Updated candidate direction

Current evidence favors:

1. **Quickadd/ctparse semantics with safe JSON scorer loading** as the primary temporal resolver;
2. **dateparser** as an independently maintained shadow/fallback for characterized compatible classes;
3. **Ada-owned typed semantic validation and zoneinfo validation** after parsing;
4. selective dual consensus rather than universal consensus.

Detailed evidence is recorded in `research/context_awareness/RESULTS-2026-09-20-RUN3.md`.

The remaining major architecture trade-off is maintenance: carrying a small auditable Quickadd safe-loader adaptation versus adopting a heavier independently maintained specialist such as Duckling. This should be resolved before ADR acceptance.

## Duckling operational characterization

A final independent specialist check was attempted against pinned upstream Duckling commit `59a13ff87b1aa8be6b93d387244f8636b26185c5`.

The upstream Docker build failed before semantic characterization. The current Dockerfile still uses `haskell:8-buster` and `debian:buster`; the runtime stage failed during `apt-get update` / package installation. Debian 10 / Buster is an archived distribution.

This is **not** counted as a temporal-semantic failure or license failure. It is direct operational/maintenance evidence:

- the upstream container path is not reproducibly buildable on the Ada target without modification;
- Ada would need to maintain a Haskell/service runtime in addition to Python;
- even the reference packaging path requires modernization before evaluation.

ADR-0007 therefore does not require Ada to patch Duckling merely to complete the benchmark. Duckling remains a future replacement/reference candidate and is not selected for the initial resolver because the evaluated container path is stale and a native/polyglot integration conflicts with the simplicity goals already accepted in ADR-0003.

Detailed evidence is recorded in `research/context_awareness/RESULTS-DUCKLING-2026-09-20.md`.

## Resolution decision policy

The resolver layer does not return a scalar confidence score. Ada instead makes a deterministic decision from typed semantic expectations, provenance, resolver evidence, and validation state.

### Typed temporal contract

The LLM performs flexible semantic extraction and provides at least:

- raw temporal expression / source span;
- expected semantic kind: `date`, `time`, `datetime`, `interval`, `duration`, or later `recurrence`;
- whether material components were explicit or require contextual derivation;
- a coarse semantic form where policy matters, e.g. absolute date, partial date, relative duration, weekday, or qualified relative weekday.

This typed contract is **not authority** and does not grant permission. It exists so deterministic code can reject incompatible parser output.

Example: for `21.10.` used as an appointment date, the expected kind is `date`. A shadow parser that reports `time` / 21:10 is non-comparable evidence, not a competing valid date.

### Canonical resolver evidence

Each resolver result is mapped into an Ada-owned canonical evidence record:

~~~text
ResolverEvidence
  resolver_id / version
  health_state
  parse_state
  semantic_kind / granularity
  normalized_value
  source_span
  parser_metadata
~~~

Parser-native types never cross the Ada port boundary.

Resolver health and per-input parse outcome are separate concepts:

- **operationally unavailable** — import/startup/health failure independent of the current expression;
- **resolved** — current expression produced a typed result;
- **unresolved** — healthy resolver found no result;
- **input error/timeout** — current expression caused a parser error or resource limit.

Only the first state permits degraded availability fallback. An input-triggered exception/timeout must **not** silently force another resolver path; it fails closed for that interpretation and is observable as a correctness/security signal.

### Evidence comparison

After canonicalization:

- **corroborated** — primary and shadow return semantically equivalent comparable values;
- **primary_valid_shadow_noncomparable** — primary matches the typed contract; shadow returns a different semantic kind/granularity;
- **primary_valid_shadow_unresolved** — primary resolves; healthy shadow does not;
- **primary_unresolved_shadow_valid** — healthy primary does not resolve; shadow resolves;
- **material_conflict** — both return comparable values for the expected kind but differ materially;
- **input_error** — at least one healthy resolver errors or times out on the current expression;
- **operational_degraded** — one resolver is independently unavailable before processing the expression;
- **invalid_or_ambiguous** — deterministic validation finds invalid wall time, unresolved policy ambiguity, impossible date, etc.

### Resolution requirements

The application/policy layer requests a `ResolutionRequirement`; the temporal resolver does not decide action risk itself.

| Resolution requirement | Meaning | Initial use |
| --- | --- | --- |
| `standard` | one validated primary result may be sufficient unless comparable evidence conflicts | reversible MVP calendar drafting/proposals |
| `corroborated` | contextual derivation requires two comparable agreeing resolvers, or an explicit deterministically validated value | future higher-consequence actions/policies |
| `explicit_only` | no contextual temporal derivation is accepted | future domains where inferred timing is unacceptable |

AdaGuard and authority checks remain downstream and independent. Satisfying a resolution requirement never grants execution permission.

### Decision table

| Situation | `standard` policy | `corroborated` policy |
| --- | --- | --- |
| Explicit complete value; deterministic validation passes | proceed; shadow optional | proceed |
| Primary + shadow agree | proceed | proceed |
| Primary valid; shadow result is incompatible with expected semantic kind | proceed, record shadow failure | do not count as corroboration; clarify unless value itself was explicit |
| Primary valid; healthy shadow unresolved | proceed only if typed/validation checks pass and no explicit ambiguity policy applies | clarify |
| Primary healthy but unresolved; shadow valid | **clarify; do not treat non-resolution as degradation or fallback authority** | **clarify** |
| Comparable primary/shadow values conflict | **clarify / no automatic proposal value** | **clarify / no automatic proposal value** |
| Primary operationally unavailable; shadow valid | degraded operation allowed after typed/deterministic checks | clarify unless value was explicit |
| Primary healthy but errors/timeouts on this input | **fail closed; do not silently fallback** | **fail closed** |
| DST nonexistent/ambiguous wall time | clarify | clarify |
| Explicit semantic ambiguity policy applies | clarify or use an explicit user preference if one exists | clarify |
| Both unresolved/invalid | clarify | clarify |

### Concrete MVP examples

- **`21.10.`** — Quickadd resolves 2026-10-21; dateparser reports a `time` result (21:10). Expected kind is `date`, so the shadow result is non-comparable. Under `standard`, Ada may use 2026-10-21 with `context_derived` provenance without asking merely because the shadow parser misclassified the expression.
- **`morgen um 16 Uhr`** — Quickadd returns the expected datetime; dateparser loses the time/granularity. Under `standard`, the valid primary result may proceed; the shadow mismatch is recorded.
- **two comparable resolvers return 16:00 vs 04:00** — material conflict; Ada asks rather than choosing one.
- **`nächsten Dienstag`** — the typed semantic form is a qualified relative weekday. German usage can be materially ambiguous, so initial policy is to clarify unless an explicit user-controlled preference later resolves this class.
- **DST fold/gap** — always clarify; parser agreement does not turn an ambiguous or nonexistent local wall time into a valid instant.

### Degraded availability

Redundancy is also an availability mechanism, but degraded mode is deliberately bounded:

- resolver availability is established independently of the current user expression;
- if the primary is operationally unavailable, dateparser may serve as fallback under `standard` only when its result matches the typed expected kind/granularity and deterministic validation succeeds;
- a current input that causes primary failure, timeout, or exception does not qualify as operational degradation;
- every degraded resolution records resolver/version/provenance so later audit can distinguish it from the normal primary path.

This prevents attacker-controlled or pathological input from deliberately knocking out the primary interpretation path merely to obtain different fallback semantics.

## Minimal Ada-owned data model

This section intentionally fixes the semantic boundaries before implementation. The types below are provisional names but their responsibilities are part of the ADR decision.

### Design rule

Keep **trusted environment context**, **untrusted semantic extraction**, **resolver evidence**, **Ada-owned resolved values**, **value derivation**, and **authorization** as separate concepts.

Do not create one generic context/provenance/confidence object that can silently accumulate authority over time.

### 1. `InterpretationContext`

Purpose: immutable trusted runtime facts that can legitimately affect interpretation.

Minimal fields:

~~~text
InterpretationContext
  now: aware datetime
  timezone: IANA timezone id
  locale: locale/language identifier
~~~

Construction:

- created by Ada/application infrastructure, never by the model;
- `now` must be timezone-aware;
- timezone must be an explicit IANA zone such as `Europe/Berlin`, not merely a UTC offset;
- locale is context for parsing, not authority.

Explicitly excluded:

- calendar IDs or provider resources;
- permissions/grants;
- actor identity/authentication assurance;
- arbitrary Memory contents;
- learned habits/preferences;
- parser policy such as `prefer_future`;
- model confidence.

Reason: adding these would turn `InterpretationContext` into a cross-domain God-object and risk conflating convenience context with authorization.

Calendar/default-calendar resolution should later have its own domain context/type. Memory-selected preferences should enter through an explicit, provenance-carrying input rather than being copied wholesale into this object.

### 2. `SourceLocator`

Purpose: identify the exact user/source material from which an expression or explicit value was derived, including multi-turn conversations.

Minimal conceptual fields:

~~~text
SourceLocator
  source_ref: opaque Ada-owned source/turn identifier
  start: integer
  end: integer
~~~

The locator references source content owned by the surrounding interaction/archive layer; it does not copy the full conversation into the temporal model.

A model-provided span or source identifier is advisory until Ada verifies it against the actual source record.

This is required because a bare character span is ambiguous once a draft is completed across multiple turns.

### 3. `TemporalExpression`

Purpose: Ada-owned normalized semantic request presented to temporal resolvers.

Minimal conceptual fields:

~~~text
TemporalExpression
  raw_text: str
  expected_kind: date | time | datetime | interval | duration | recurrence
  semantic_form: absolute | partial | relative | weekday | qualified_weekday | other
  source: verified SourceLocator
~~~

`raw_text` is still untrusted user/model-derived content. `expected_kind` and `semantic_form` are semantic claims, not facts or authority.

`source` is accepted into the Ada-owned type only after deterministic verification against the referenced source record. A model-provided source reference or offset is advisory until verified.

Explicitly excluded:

- normalized date/time values;
- permissions;
- target calendar;
- confidence probability;
- resolver choice;
- fallback decision.

Reason: this type says *what needs interpretation*, not *what the answer is*.

### 4. `TemporalResolutionPolicy`

Purpose: version the deterministic interpretation defaults that are neither environment facts nor user authority.

Conceptually:

~~~text
TemporalResolutionPolicy
  policy_id: str
  version: str
  date_order: DMY | MDY | YMD
  incomplete_date_direction: future | past | nearest
  qualified_weekday_policy: clarify | configured_semantics
~~~

Adapters map this Ada-owned policy to parser-specific settings such as dateparser's `PREFER_DATES_FROM` or Quickadd's date format.

The policy is not part of `InterpretationContext` because changing a parsing rule is a product-policy/configuration change, not a change in the current environment.

The policy is recorded in `ValueDerivation` so a context-derived value can be reconstructed later.

It contains no permissions, identity, or learned Memory preferences.

### 5. `ResolverEvidence`

Purpose: canonical Ada-owned representation of one resolver's observation.

Minimal conceptual fields:

~~~text
ResolverEvidence
  resolver_id: str
  resolver_version: str
  operational_state: available | unavailable
  parse_state: resolved | unresolved | input_error | timeout
  semantic_kind: optional TemporalKind
  granularity: optional parser-independent granularity
  normalized_value: optional canonical temporal value
~~~

`operational_state` is established independently of the current expression. This is necessary to distinguish genuine degraded availability from an input-triggered failure.

Parser-specific objects and arbitrary metadata do not cross the port boundary.

Explicitly excluded:

- arbitrary parser-native metadata dictionaries;
- model confidence;
- authorization/permission state;
- automatic decision such as 'accept this result';
- raw secrets or unrelated source text.

Reason: evidence must remain comparable across Quickadd, dateparser, or future resolvers.

### 6. `ValueDerivation`

Purpose: explain how a material resolved value came to exist.

The name deliberately differs from Ada's existing `InstructionProvenance`, which answers a different security question: where an instruction came from.

Initial derivation kinds:

~~~text
explicit
context_derived
defaulted
~~~

`memory_derived` is deliberately **not** added by this ADR. Memory semantics and trust are a separate upcoming architecture decision; that ADR may extend the derivation model later.

For a context-derived temporal value the derivation records only the minimum reconstructable basis, conceptually:

~~~text
ValueDerivation
  kind
  source: SourceLocator
  reference_time
  timezone
  locale
  resolution_policy_id / version
  supporting_resolver_ids / versions
~~~

Not every field is present for every derivation kind.

Explicitly excluded:

- permission/authority;
- actor identity;
- general Memory snapshot;
- full conversation history;
- secret/provider credentials;
- a numerical confidence score.

`explicit` may be assigned only when Ada deterministically corroborates the material temporal components against the verified source record; a model cannot make a value explicit merely by labeling it so.

Rule: **derivation can explain a value but can never authorize an action**.

### 7. `TemporalResolution`

Purpose: Ada-owned validated interpretation result after resolver comparison and deterministic temporal validation.

Conceptually:

~~~text
TemporalResolution
  semantic_kind
  canonical_value
  derivation: ValueDerivation
  resolution_state
~~~

Initial `resolution_state` is one of:

- `resolved`;
- `needs_clarification`;
- `invalid`;
- `operationally_degraded`.

A `TemporalResolution` is **not an executable action proposal**. It may be used by application code to complete a non-executable draft. Only the existing later application step may construct an executable `CreateCalendarEventProposal`, which must still pass Ada-owned validation and AdaGuard.

Resolver evidence may be attached to an ephemeral resolution trace for diagnostics/audit, but full evidence objects should not automatically become part of executable proposal identity or durable action payloads.

Reason: action identity should describe *what Ada intends to do*, not which parser happened to produce the date.

### 8. `ResolutionRequirement`

Purpose: caller-requested interpretation strictness.

~~~text
ResolutionRequirement
  standard
  corroborated
  explicit_only
~~~

This replaces the ambiguous phrase 'interpretation assurance'. It must not be confused with the existing `AuthenticationAssurance` used by authorization.

Explicit rule:

~~~text
ResolutionRequirement != AuthenticationAssurance != Permission
~~~

A high-resolution requirement cannot grant authority. Strong authentication cannot turn an ambiguous date into an unambiguous one. Resolver agreement cannot increase channel authentication.

### Why there is no `ConfidenceScore`

Ada deliberately does not introduce a cross-parser/model numerical confidence score in this slice.

Reasons:

- Quickadd and dateparser scores/metadata are not calibrated against each other;
- a precise-looking number would obscure categorical failures such as wrong semantic kind;
- security behavior should depend on explicit states and policies, not an arbitrary threshold;
- confidence does not equal authority.

The useful signals are categorical and inspectable: expected kind, resolved/unresolved, comparable/non-comparable, agreement/conflict, explicit/context-derived, valid/ambiguous/invalid, and operational health.

### Separation from existing calendar types

`CreateCalendarEventDraft` remains the non-executable domain intent and `CreateCalendarEventProposal` remains the executable proposal shape.

ADR-0007 does **not** add temporal resolver fields directly to `CreateCalendarEventProposal` and does not change its action binding.

The intended application flow is:

~~~text
model output / draft
        ↓
verified TemporalExpression(s)
        ↓
InterpretationContext + TemporalResolutionPolicy + ResolutionRequirement
        ↓
TemporalResolverPort(s) -> ResolverEvidence
        ↓
Ada resolution policy + zoneinfo validation
        ↓
TemporalResolution + ValueDerivation
        ↓
completed non-executable draft
        ↓
existing proposal construction / validation
        ↓
AdaGuard
~~~

This keeps framework choice, parser choice, derivation evidence, action identity, and authorization independently replaceable.

## Acceptance criteria for ADR-0007

The proposed resolver strategy can move from Proposed to Accepted only when:

1. the representative characterization corpus and explicit ambiguity policies are documented;
2. no Ada-owned natural-language dictionary is required for ordinary temporal interpretation;
3. ambiguous, invalid, or conflicting values fail safely without forcing verbose input for obvious context;
4. the selected primary and shadow adapters map into Ada-owned evidence/derivation types without leaking framework-specific types into core;
5. license and NOTICE obligations are compatible with Ada's project/distribution strategy;
6. the complete production dependency graph is pinned/auditable rather than only top-level packages;
7. the Quickadd primary path has a reproducible, versioned, integrity-checked JSON scorer artifact and does not deserialize pickle in Ada's normal build/runtime path;
8. the selected production adapters are validated in Ada's supported Python/container deployment path, including the future Linux path before that path is claimed supported;
9. resolver operational health is established independently from per-expression parse outcomes;
10. replacement through the Ada-owned temporal resolver port remains practical.

The current research closes the semantic-feasibility question but **does not yet close items 6-8**. Therefore ADR-0007 remains Proposed.

## Characterization harness

The disposable research harness lives under `research/context_awareness/`.

Current research variants include:

1. dateparser 1.4.3;
2. Acreom Quickadd pinned to commit `0b3bfc26a7347a80821e86eb3838556a7adc2a30`;
3. Quickadd with its scorer disabled, used only to characterize scorer importance;
4. Quickadd with the trained scorer reconstructed from primitive JSON;
5. an optional pinned-source Duckling container benchmark, which currently fails in the upstream Buster-based build before semantic execution.

The Python candidates are installed into isolated temporary virtual environments and are not Ada product dependencies.

The comparison records `agreement`, `interpretation_conflict`, `single_resolver_result`, `input_error`, and `unresolved`. These are research-result states, not runtime health states.

## Remaining follow-ups before acceptance

1. define the production-safe Quickadd JSON artifact generation/provenance/integrity process;
2. capture a fully resolved production dependency lock rather than relying on top-level pins;
3. characterize the selected adapters in the intended Ada container/runtime profile and retain Linux validation as a prerequisite before claiming Linux support;
4. convert the proposed conceptual types/port into an implementation plan without changing the existing Draft -> Proposal -> AdaGuard authority boundary;
5. independently review the corrected ADR/research evidence.

Only after these follow-ups should ADR-0007 move from Proposed to Accepted.
