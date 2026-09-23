# Ada Memory architecture decision matrix

- **Status:** Draft for maintainer review
- **Date:** 2026-09-23
- **Evidence base:** completed executable comparison of ReMe 0.4.1.12, LangMem 0.0.30, Hindsight 0.10.1, Letta Code/MemFS 0.32.15
- **Model baseline:** local `qwen3.5:9b`
- **Purpose:** compare viable Memory architecture roles, not force a single-framework winner

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

## Proposed weights

The weighting reflects Ada's confirmed product constraints: correctness and inspectability before sophistication.

| Criterion | Weight | Why it matters |
| --- | ---: | --- |
| Human-readable/editable authoritative truth | 18% | Core Ada requirement: user-owned Markdown/YAML, inspectable and editable outside Ada |
| Correction / contradiction semantics | 16% | Explicit correction must differ from unresolved conflict |
| Provenance integrity / explainability | 14% | Important memories must remain attributable; fabricated provenance is unacceptable |
| Privacy / scope / isolation | 12% | Private/shared household boundaries must not collapse |
| Forget / rebuild / lifecycle | 10% | Operational deletion and recovery from outside edits are core trust requirements |
| Retrieval / context efficiency | 8% | Memory must remain useful without loading everything into context |
| Local/offline + resource fit | 7% | MVP target includes Apple Silicon / constrained local execution |
| Integration fit with Ada architecture | 6% | Avoid replacing accepted PydanticAI, DBOS, Cedar/AdaGuard boundaries |
| Operational / maintenance simplicity | 5% | Family assistant should remain maintainable, not become a platform project |
| Portability / replaceability | 4% | Data and implementation should remain movable to later Linux/vServer deployment |
| **Total** | **100%** | |

## Scoring scale

- **5** — strong demonstrated fit
- **4** — good fit with bounded adapter/validation
- **3** — mixed; useful but material gap
- **2** — significant gap or architectural friction
- **1** — poor fit / capability not provided
- **0** — incompatible hard gate

Scores distinguish **demonstrated behavior** from hypothetical future capability.

## Weighted matrix

| Criterion | Weight | ReMe | LangMem | Hindsight | Letta/MemFS | ReMe + LangMem | ReMe + Hindsight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Human-readable/editable authoritative truth | 18 | 5.0 | 1.0 | 1.0 | 4.0 | 5.0 | 5.0 |
| Correction / contradiction semantics | 16 | 3.0 | 4.5 | 2.0 | 4.0 | 4.5 | 2.5 |
| Provenance integrity / explainability | 14 | 4.0 | 2.5 | 2.5 | 1.5 | 4.0 | 3.0 |
| Privacy / scope / isolation | 12 | 3.0 | 3.0 | 4.0 | 2.0 | 3.5 | 4.0 |
| Forget / rebuild / lifecycle | 10 | 5.0 | 2.5 | 4.5 | 2.0 | 5.0 | 5.0 |
| Retrieval / context efficiency | 8 | 3.0 | 3.5 | 4.5 | 3.5 | 3.5 | 4.5 |
| Local/offline + resource fit | 7 | 4.0 | 4.0 | 2.5 | 3.0 | 3.5 | 2.0 |
| Integration fit with Ada architecture | 6 | 2.0 | 4.0 | 3.0 | 1.0 | 2.0 | 2.0 |
| Operational / maintenance simplicity | 5 | 2.5 | 4.0 | 2.0 | 2.0 | 1.5 | 1.0 |
| Portability / replaceability | 4 | 4.0 | 4.0 | 2.5 | 3.0 | 4.0 | 3.0 |
| **Weighted result / 100** | **100** | **74.5** | **60.4** | **53.9** | **55.6** | **79.6** | **69.8** |

The numeric result is a decision aid, not a proof.

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

This is the strongest evidence-backed composite in the current matrix.

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

## Sensitivity

The current result is not driven only by low-level implementation convenience.

Even with substantially higher weight on integration/operational simplicity and somewhat lower weight on correction/provenance, the relative pattern remains:

1. ReMe + LangMem
2. ReMe
3. ReMe + Hindsight
4. LangMem
5. Letta/MemFS / Hindsight

The exact numeric distance changes, but the architectural conclusion is stable:

- **ReMe is the best demonstrated authoritative substrate.**
- **LangMem is the most promising reusable semantic-change helper.**
- **Hindsight is the strongest specialized derived-learning/recall candidate, but not required for MVP.**
- **Letta/MemFS is valuable architecture reference material but does not justify runtime adoption from current evidence.**

## Draft architecture implication

The smallest reuse-first direction supported by current evidence is:

```text
Authoritative Memory
Markdown/YAML in protected vaults
        │
        ▼
ReMe substrate
files / watch / rebuild / simple retrieval
        │
        ├───────────────┐
        ▼               │
LangMem proposal        │
(extract/update)        │
        │               │
        ▼               │
Ada deterministic       │
validation + AdaGuard   │
        │               │
        └──── write ─────┘

Optional later derived layers:
- Hindsight, only if richer learning/recall shows material benefit;
- graph/vector indexes, only if simpler retrieval is insufficient.
```

This is a **draft implication**, not yet an accepted ADR decision.

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
