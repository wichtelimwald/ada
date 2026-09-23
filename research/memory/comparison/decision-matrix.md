# Ada Memory architecture decision matrix

- **Status:** Draft for maintainer review
- **Date:** 2026-09-23
- **Evidence base:** completed executable comparison of ReMe 0.4.1.12, LangMem 0.0.30, Hindsight 0.10.1, Letta Code/MemFS 0.32.15
- **Model baseline:** local `qwen3.5:9b`
- **Purpose:** first agree criteria and weights; only then score viable Memory architecture roles

This matrix is deliberately separate from ADR acceptance. The weights and scores are a research proposal and must be reviewed before they become decision evidence.

## Hard-gate observations

| Gate | ReMe | LangMem | Hindsight | Letta/MemFS |
| --- | --- | --- | --- | --- |
| Permissive project license | PASS — Apache-2.0 | PASS — MIT | PASS — MIT | PASS — Apache-2.0 |
| Local/offline execution demonstrated | PASS | PASS | PASS | PASS |
| Human-readable authoritative Memory provided by candidate | **PASS** | **NO — caller-owned store** | **NO — database bank is primary** | PARTIAL — Git-backed Markdown, but out-of-band edit/rebuild/forget/isolation not fully characterized |
| Out-of-band edit + rebuild demonstrated | **PASS** | N/A / caller responsibility | NO | NOT CHARACTERIZED |
| Operational forget demonstrated | **PASS** | caller/store responsibility; not exercised | **PASS** | NOT CHARACTERIZED |
| Unresolved contradiction preserved safely as canonical truth | PARTIAL — source notes remain separate; derived Dream is unreliable | **GOOD structurally**, but provenance was invented for one claim | **FAIL if observation is canonical** — conflict collapsed to 17:00 | GOOD structurally, but provenance tokens were corrupted/invented |
| Provenance integrity suitable for authoritative use without validation | PARTIAL/GOOD at source-note layer | PARTIAL | **NO** for consolidated observations | **NO** in characterized run |
| Fit with accepted Ada runtime without replacing PydanticAI/DBOS/AdaGuard | PARTIAL — AgentScope coupling | GOOD/PARTIAL — Python but LangChain family dependency | PARTIAL — separate DB/service subsystem | POOR for wholesale adoption — Node/Letta runtime coupling |

The hard-gate table already rules out treating LangMem or Hindsight **alone** as Ada's authoritative Memory store under the confirmed Markdown-first direction.

It also means Letta/MemFS cannot be selected as the authoritative store from current evidence without more characterization.

## Agreed criteria and weights

The criteria and weights were agreed **before candidate scoring** and are now frozen for this decision round.

License compatibility remains a **hard gate**, not a weighted criterion. Likewise, Ada's trust invariant `Memory != Permission` is an architecture constraint rather than something a candidate can compensate for with points elsewhere.

| Criterion | Weight | Includes |
| --- | ---: | --- |
| **Authoritative Memory fit** | **20%** | human-readable/user-owned source of truth, external editability, rebuild, forget |
| **Semantic correctness & provenance** | **20%** | correction vs contradiction, source integrity, no invented facts/metadata, explainability |
| **Privacy & isolation** | **20%** | private/shared boundaries, person/vault/bank isolation, no scope leaks |
| **Retrieval & learning quality** | **20%** | recall, consolidation/learning, context efficiency, growth to larger Memory |
| **Architecture & operational fit** | **20%** | fit with PydanticAI/DBOS/AdaGuard, local/offline operation, dependencies, resources, maintenance, portability |
| **Total** | **100%** | |

The five criteria intentionally combine previously overlapping dimensions so the same underlying property is not rewarded multiple times.

## Scoring scale

- **5** — strong demonstrated fit
- **4** — good fit with bounded adapter/validation
- **3** — mixed; useful but material gap
- **2** — significant gap or architectural friction
- **1** — poor fit / capability not provided
- **0** — incompatible hard gate

Scores distinguish **demonstrated behavior** from hypothetical future capability.

## Scoring result

The five criteria and 20% weights were frozen before scoring.

A hard-gate failure is **not compensable by weighted points**. Scores for gate-failing standalone candidates are retained only to show component strengths and weaknesses; they are not decision-eligible architectures.

| Option | Authoritative Memory fit | Semantic correctness & provenance | Privacy & isolation | Retrieval & learning quality | Architecture & operational fit | Weighted result | Decision status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **ReMe + LangMem** | 5.0 | 4.0 | 4.0 | 4.0 | 2.5 | **78 / 100** | **Viable composite** |
| **ReMe** | 5.0 | 3.0 | 4.0 | 3.0 | 3.0 | **72 / 100** | **Viable baseline** |
| **ReMe + Hindsight** | 5.0 | 3.0 | 4.0 | 4.0 | 2.0 | **72 / 100** | **Viable composite, extra complexity** |
| **LangMem** | 0.0 | 4.0 | 3.0 | 4.0 | 4.0 | **60 / 100** | **Not viable standalone — no authoritative store** |
| **Hindsight** | 0.0 | 2.0 | 4.0 | 4.5 | 2.5 | **52 / 100** | **Not viable standalone — DB is primary truth** |
| **Letta/MemFS** | 4.0 | 2.0 | 2.0 | 3.0 | 2.0 | **52 / 100** | **Not decision-ready — provenance failure; forget/isolation uncharacterized** |

Because all criteria are equally weighted, the weighted result is simply the mean criterion score scaled to 100.

### Score rationale by criterion

#### 1. Authoritative Memory fit

- **ReMe — 5.0:** demonstrated Markdown/YAML truth, outside edit, clean rebuild, and operational forget.
- **LangMem — 0.0 standalone:** storage-agnostic helper; it does not provide Ada's required authoritative human-readable store.
- **Hindsight — 0.0 standalone:** database memory bank is primary state; this violates the confirmed authoritative-Memory direction.
- **Letta/MemFS — 4.0:** Git-backed human-readable Markdown is close, but outside-edit/rebuild and forget behavior were not fully characterized.
- **ReMe composites — 5.0:** ReMe remains authoritative; the second component is derived/advisory.

#### 2. Semantic correctness & provenance

- **ReMe — 3.0:** source notes preserve the tested facts/conflicts, but Dream/consolidation is nondeterministic and one run contradicted corrected source text.
- **LangMem — 4.0:** strongest tested correction/conflict behavior; loses a point because it invented a provenance value when the fixture provided none.
- **Hindsight — 2.0:** explicit correction is recognized, but consolidation invented a validity interval and collapsed an unresolved conflict while mixing provenance.
- **Letta/MemFS — 2.0:** correction/conflict representation is readable, but evidence identifiers were reformatted, truncated, and invented.
- **ReMe + LangMem — 4.0:** ReMe can retain authoritative source/provenance while LangMem proposes structured semantic changes; still requires deterministic validation before write.
- **ReMe + Hindsight — 3.0:** keeping ReMe authoritative limits damage, but Hindsight observations remain unsafe as canonical semantic truth.

#### 3. Privacy & isolation

- **ReMe — 4.0:** separate-workspace canary isolation is demonstrated; Ada's full household protection-domain topology still needs enforcement outside the model.
- **LangMem — 3.0:** namespaces/store isolation are caller-owned rather than a demonstrated protection-domain implementation.
- **Hindsight — 4.0:** native memory-bank isolation passed cross-bank canary checks; relevance validation is still needed because absent-token queries can return similar in-bank memories.
- **Letta/MemFS — 2.0:** protection-domain isolation was not characterized.
- **ReMe + LangMem — 4.0:** ReMe workspaces plus caller-controlled LangMem namespaces fit the intended partitioning, but Ada still owns enforcement.
- **ReMe + Hindsight — 4.0:** both layers can be partitioned, but duplicate scope enforcement across two stores increases operational care.

#### 4. Retrieval & learning quality

- **ReMe — 3.0:** useful file-native retrieval and Dream concepts, but consolidation integration failed 0/3 in the comparison run.
- **LangMem — 4.0:** strong structured extraction/update behavior and good conflict preservation; it is not itself the retrieval substrate.
- **Hindsight — 4.5:** strongest specialized recall/observation capability, fast direct recall, source-fact links, and useful consolidation; local Reflect is too slow and observation semantics need validation.
- **Letta/MemFS — 3.0:** useful persistent agent-memory behavior, but the comparison focused on persistence rather than proving superior retrieval/learning quality.
- **ReMe + LangMem — 4.0:** combines adequate file retrieval with the strongest tested semantic update helper without adding a second database service.
- **ReMe + Hindsight — 4.0:** powerful derived recall, but the score is capped because the composite itself was not exercised and Hindsight's preferred observations can be semantically unsafe.

#### 5. Architecture & operational fit

- **ReMe — 3.0:** local Python path works, but AgentScope is a meaningful dependency/runtime coupling beside PydanticAI.
- **LangMem — 4.0:** Python, storage-agnostic, and comparatively easy to place behind an Ada-owned interface; LangChain-family dependency remains a cost.
- **Hindsight — 2.5:** local execution works, but pg0, ONNX embeddings, a service process, substantial dependencies/resource use, and optional Reflect latency add operational weight.
- **Letta/MemFS — 2.0:** whole-framework adoption introduces Node/Letta runtime coupling alongside Ada's already accepted Python/PydanticAI architecture.
- **ReMe + LangMem — 2.5:** two dependency ecosystems lower simplicity, but both can remain behind narrow Ada interfaces and avoid a second database service.
- **ReMe + Hindsight — 2.0:** two subsystems plus database/service/embedding infrastructure is materially heavier for the MVP.

### Interpretation

The Markdown + captured Git history + basic-search control is not scored in
this matrix. Its omission matters: a six-point lead for ReMe + LangMem over
ReMe alone does not establish that either component is necessary for Ada's
MVP. Measure the control against the same hard gates and criteria before a
backend decision; do not assign it hypothetical points.

The frozen matrix supports three scored ReMe-containing options:

1. **ReMe + LangMem — 78/100**
   - strongest combined fit;
   - ReMe owns human-readable authoritative Memory;
   - LangMem is a semantic-change **proposal** helper only;
   - deterministic provenance/scope/correction validation remains Ada-owned.

2. **ReMe — 72/100**
   - simplest scored framework baseline;
   - strongest demonstrated authoritative substrate;
   - weaker semantic learning/consolidation can initially be constrained rather than replaced.

3. **ReMe + Hindsight — 72/100**
   - much stronger specialized retrieval/learning than ReMe alone;
   - no total-score advantage because operational complexity and unsafe observation consolidation offset that benefit;
   - best treated as an optional later derived layer if real-world retrieval evidence justifies it.

LangMem and Hindsight remain valuable components despite failing as standalone authoritative architectures. Letta/MemFS remains useful design reference material but current evidence does not justify another characterization round for the MVP.

## Evidence behind the main score differences

### ReMe

Why it scores well:

- strongest demonstrated fit for Ada's authoritative file-native source;
- ordinary Markdown/YAML;
- clean out-of-band edit -> rebuild;
- operational forget -> rebuild;
- workspace isolation;
- good source-conversation provenance;
- portable files.

Why it loses points:

- model-generated Dream/consolidation is not deterministic enough to be authoritative;
- one run inverted correction semantics in derived text, while a later run did not;
- later Auto Dream extracted plausible units but integrated 0/3;
- AgentScope is a real runtime/dependency coupling despite Ada using PydanticAI.

### LangMem

Why it scores well:

- best demonstrated structured correction behavior;
- updated the same memory ID Wednesday -> Thursday;
- kept 16:00 and 17:00 as separate unresolved claims;
- storage-agnostic API makes it possible to keep another store authoritative;
- Python and local Ollama path integrate more naturally than a second full agent runtime.

Why it loses points:

- it is not a complete authoritative store;
- when a provenance field was required but no token existed, the model invented a synthetic `SESSION_...` evidence value;
- caller still owns persistence, privacy domains, versioning, forgetting, and rebuild behavior.

### Hindsight

Why it scores well:

- evidence-backed source facts and observations;
- fast direct recall after ingestion;
- native memory-bank isolation;
- explicit document deletion works;
- strong derived-learning/retrieval model.

Why it loses points:

- DB/bank is primary state rather than human-owned Markdown;
- correction consolidation invented an unsupplied validity interval;
- unresolved 16:00/17:00 conflict was collapsed into a preferred 17:00 observation;
- that observation incorrectly inherited the evidence token from the 16:00 claim;
- local agentic Reflect exceeded practical latency with `qwen3.5:9b`;
- pg0 + ONNX + service process is materially heavier operationally.

### Letta/MemFS

Why it scores well:

- human-readable Git-backed Markdown;
- explicit correction represented clearly;
- unresolved pickup claims remained separate;
- architecture is useful reference material for file-native agent memory.

Why it loses points:

- evidence identifiers were reformatted, truncated, and invented in the characterized run;
- generated text subsequently claimed those identifiers had been preserved verbatim;
- forget and protection-domain isolation remain uncharacterized;
- whole-framework use would introduce Node/Letta runtime coupling alongside Ada's accepted Python/PydanticAI runtime.

## Composite options

### ReMe + LangMem

This is the highest-scoring decision-eligible option under the frozen five-criterion matrix.

Potential role split:

```text
human-owned Markdown/YAML
        │
       ReMe
 file/watch/rebuild/search
        │
        ▼
  candidate semantic change
        │
      LangMem
 structured insert/update proposal
        │
        ▼
deterministic Ada validation
 provenance / scope / correction intent
        │
        ▼
authoritative Markdown write
```

Important: LangMem must **not** write fabricated provenance into authoritative Memory. Provenance/source IDs should be caller-supplied deterministic fields or the change proposal must be rejected.

This composite still carries two dependency ecosystems:
- ReMe -> AgentScope;
- LangMem -> LangChain-family dependencies.

The score therefore intentionally penalizes operational simplicity and integration fit.

### ReMe + Hindsight

Potential role split:

```text
ReMe Markdown truth
      │
      └──> rebuildable Hindsight bank
             derived observations / recall
```

This makes more sense than Hindsight as authoritative Memory because source truth remains outside Hindsight.

However, the characterized contradiction/provenance behavior means Ada must never consume a Hindsight observation as authoritative without checking the underlying source facts and scope.

For the MVP, the extra database/service/embedding subsystem is difficult to justify unless retrieval quality proves decision-changing.

## Minimal-custom control

A minimal Ada implementation remains the **control/fallback**, not a scored preferred option.

It would be unfair to give an unimplemented custom solution high numeric scores merely because it could theoretically match every requirement.

Custom work should only be justified for the smallest deterministic seams that no reusable component can safely own, for example:

- validating that a proposed source/provenance identifier actually came from the caller/source;
- deciding whether input explicitly means correction versus unresolved contradiction;
- enforcing protection-domain placement through AdaGuard;
- preventing derived/model-generated state from becoming authority.

This is very different from writing a complete Ada Memory engine.

## Next step

The scoring step is complete.

Before converting the matrix result into an ADR decision:

1. review any **disputed individual scores** against the recorded evidence; do not change the frozen weights after seeing the result;
2. run a small score-sensitivity check around genuinely disputed cells;
3. complete the transitive license/security review for the likely dependency path;
4. define the minimal deterministic validation boundary around LangMem proposals;
5. close external document-reference/lifecycle fit;
6. obtain independent review.

## Remaining gates before ADR acceptance

1. Maintainer review/adjustment of weights and any disputed scores.
2. Exact transitive license/security review of the intended dependency path, especially ReMe -> AgentScope and LangMem/LangChain dependencies.
3. Define the narrow deterministic boundary between:
   - model-generated semantic proposal;
   - provenance/scope validation;
   - authoritative write.
4. External document-reference/lifecycle characterization.
5. Independent review of the decision evidence.
6. Explicit maintainer acceptance of ADR-0008.
