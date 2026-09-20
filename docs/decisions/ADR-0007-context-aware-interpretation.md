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
  known/default calendars
  later: selected user-controlled preferences/memory facts
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

A resolved material field must be able to distinguish at least:

- explicit — directly stated by the user/source;
- context_derived — derived from trusted runtime context;
- defaulted — filled from an explicit user/system default;
- later, memory_derived — supplied from authoritative user-controlled Memory.

Example:

~~~
raw:       "21.10."
resolved:  2026-10-21
provenance:
  kind: context_derived
  basis:
    reference_date: 2026-09-20
    timezone: Europe/Berlin
    policy: prefer_future
~~~

Provenance describes why a value is present. It does not grant authority.

### 5. Put temporal parsing behind an Ada port

Do not expose one library's result model through Ada core.

A future implementation should define a small Ada-owned TemporalResolverPort (name provisional) so that dateparser, quickadd, Duckling, or another implementation can be characterized or replaced without changing action semantics.

### 6. Do not adopt a temporal library until characterization passes

dateparser is the **preferred first candidate**, not yet an accepted dependency.

quickadd is the most interesting specialist benchmark for Ada's appointment-oriented language.

Duckling and Microsoft Recognizers-Text remain reference benchmarks.

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

### Weighted decision matrix

Only candidates that pass all hard gates are scored.

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

The characterization step will evaluate four operational states:

- **agreement** — both resolvers produce the same normalized semantic result;
- **interpretation_conflict** — both produce results but disagree semantically;
- **degraded_single_resolver** — only one resolver is available or can resolve the expression;
- **unresolved** — neither resolves the expression.

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
| Privacy/security fit | PASS in current review | **TBD** — import-time pickle loading of bundled scoring model requires explicit hardening decision |
| Supported target deployment | PASS — documented Python 3.14 | PASS on target Mac by characterization; Linux still to retain as supported path |
| Reproducible dependency path | PASS — pinned release | PASS — pinned Git commit, but weaker distribution ergonomics |

Because TBD is not a pass, quickadd is **not yet eligible for final selection** despite its stronger behavioral result.

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

Do not interpret these numbers as the decision while quickadd's security gate remains TBD.

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

## Acceptance criteria for the implementation choice

The candidate can be accepted only if:

1. the characterization suite passes with explicit documented policies;
2. no Ada-owned natural-language dictionary is required for ordinary date interpretation;
3. ambiguous or invalid values can fail safely without forcing verbose user input for obvious context;
4. the dependency runs locally and cleanly on Python 3.14 / target Mac;
5. license and NOTICE requirements are compatible with Ada;
6. parser output can be mapped into Ada-owned provenance without leaking framework-specific types into core;
7. replacement remains practical.

## Characterization harness

A disposable research harness lives under `research/context_awareness/`.

Initial executable candidates:

1. dateparser 1.4.3;
2. Acreom quickadd pinned to a concrete commit.

Each candidate is installed into an isolated temporary virtual environment and is not added to Ada's product dependencies.

The harness records normalized results plus the redundancy states `agreement`, `interpretation_conflict`, `degraded_single_resolver`, and `unresolved`.

Duckling and Microsoft Recognizers-Text remain secondary benchmarks where the additional setup cost is justified by unresolved questions from the first comparison.

After the characterization results, update this ADR with:

- hard-gate outcomes;
- the completed weighted matrix;
- the selected temporal resolver strategy;
- whether runtime redundancy is single-primary, primary+shadow, selective dual-consensus, or another explicitly justified policy;
- dependency/version and ambiguity policies.

Only then should ADR-0007 move from Proposed to Accepted.
