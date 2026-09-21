# ReMe scenario matrix against ADR-0008

- **Status:** Research in progress
- **Date:** 2026-09-21
- **Upstream:** https://github.com/agentscope-ai/ReMe
- **Basis:** ADR-0008 representative Memory scenarios

Legend:

- **NATIVE** — ReMe has a direct mechanism close to Ada's requirement.
- **NATIVE / CHARACTERIZE** — mechanism exists but exact Ada behavior must be proven by an executable scenario.
- **ADAPTER** — ReMe can likely be used, but Ada must supply deterministic semantics/boundary logic.
- **GAP** — no sufficiently matching mechanism has been identified.
- **ADA-OWNED** — requirement intentionally belongs outside ReMe.

| # | Ada scenario | ReMe fit | Assessment |
| ---: | --- | --- | --- |
| 1 | Personality bootstrap | **ADAPTER** | ReMe can store/edit Markdown, but it has no Ada personality seed-once/existing-wins lifecycle. Ada owns bootstrap and writes the resulting profile into the appropriate vault/workspace. |
| 2 | Outside edit | **NATIVE / CHARACTERIZE** | File editing while stopped is consistent with ReMe's file-source design. Startup/watchers can rebuild metadata, but full rebuild behavior must be tested; `reindex` alone is insufficient. |
| 3 | Correction | **ADAPTER** | Auto Dream supports `CORRECT`, but Ada's explicit `superseded` state and confirmation basis are not native. |
| 4 | Contradiction | **GAP / ADAPTER** | ReMe can annotate conflicting evidence, but its prompts may reconcile/tighten the claim. Ada requires two credible explicit claims to remain visibly unresolved unless deterministically corrected. |
| 5 | Private/shared scope | **ADA-OWNED + CHARACTERIZE** | One ReMe workspace can plausibly map to one protection domain. Ada must choose which workspaces are accessible and create permitted minimized shared derivatives. |
| 6 | Provenance after source deletion | **ADAPTER** | Digest nodes retain source links, but source deletion/lifecycle semantics are not Ada's minimized non-resolvable provenance contract. Need source-ref degradation behavior. |
| 7 | Forget | **NATIVE / CHARACTERIZE** | Current-file deletion is watched and derived index entries are pruned. Must prove forgotten content does not return after full metadata rebuild. |
| 8 | No authority from learning | **ADA-OWNED** | ReMe is not an authorization engine. AdaGuard remains mandatory. |
| 9 | No archive rescan | **ADA-OWNED / ADAPTER** | ReMe retains session source by default. Ada must control whether/when session material may be reprocessed after a deliberate forget. |
| 10 | Offline recall | **NATIVE / CHARACTERIZE** | BM25 and explicit-link retrieval are local and do not require a cloud LLM. End-to-end Ada local configuration still needs testing. |
| 11 | Gardening | **ADAPTER** | Auto Dream consolidates/refines/corrects automatically. Ada requires inspectable/confirmable destructive or material restructuring, so policy and proposal mode must wrap it. |
| 12 | Preference learning | **ADAPTER** | ReMe can corroborate/refine preferences, but lacks Ada's `provisional -> confirmed/observed_pattern|explicit_user` contract. |
| 13 | Routine learning | **ADAPTER** | ReMe can consolidate recurring procedures/patterns; Ada must own maturity and ensure routine never becomes authority. |
| 14 | Learning correction | **ADAPTER** | `CORRECT` exists, but user rejection, lifecycle state, and archive no-relearn behavior require Ada semantics. |
| 15 | Pattern aging | **GAP / ADAPTER** | No matching category-specific observed-pattern aging state was found. ReMe can use dates/search but does not expose Ada's `stale` lifecycle. |
| 16 | Contradictory explicit statements | **GAP / ADAPTER** | ReMe's conflict reconciliation does not guarantee unresolved `contradicted` state for two credible explicit claims. |
| 17 | Explicit correction | **ADAPTER** | ReMe can `CORRECT`; Ada must deterministically preserve old/new lifecycle and `explicit_user` confirmation basis. |
| 18 | Private vault isolation | **ADAPTER / CHARACTERIZE** | Separate workspaces are the promising topology. ReMe itself has no general-purpose user authentication/household model. Need multi-Application isolation/resource test. |
| 19 | Shared derivative provenance | **ADA-OWNED** | Cross-protection-domain minimized derivatives and redacted provenance are an Ada privacy-policy function. |
| 20 | Version recovery | **ADA-OWNED** | ReMe does not require Git. Ada's per-vault Git/versioning layer should provide rollback independently. |
| 21 | Operational forget with history | **NATIVE + ADA-OWNED HISTORY** | ReMe current-state deletion/index pruning fits operational forget; Git/history is external to ReMe and must not be queried by normal Ada retrieval. |
| 22 | Selective retention | **PARTIAL / ADAPTER** | Auto Memory prompts select useful preferences/facts/decisions/experience and Auto Dream distills further, but Ada's class/sensitivity/retention policy is not a deterministic ReMe contract. |
| 23 | Per-interlocutor adaptation | **ADAPTER** | `digest/personal` can store person-specific preferences, but Ada must separate global personality, interaction profile, person facts, and protection domains. |
| 24 | Conversation continuity | **NATIVE / ADAPTER** | `session -> daily -> digest` strongly matches episodic consolidation. Ada must control transcript retention and define the episode schema. |
| 25 | Referenced school letter | **GAP / ADAPTER** | ReMe expects resource bytes/files inside `resource/`. Ada wants an external provider-independent reference with optional materialization. |
| 26 | Unavailable source document | **GAP / ADAPTER** | ReMe's normal resource model assumes a workspace source. Ada must represent source availability independently from the retained summary. |
| 27 | Source/memory lifecycle separation | **GAP / ADAPTER** | Ada must distinguish forgetting a summary from deleting the external source document; ReMe's resource file and memory pipeline do not provide this provider-boundary contract. |

## Summary counts

Using the strictest classification per row:

- strong/native fit: **6** scenarios (mostly file/index/episodic mechanics);
- adapter/Ada-owned fit: **15** scenarios;
- material gaps requiring new semantics or extension: **6** scenarios.

The count alone is not a score. Many adapter rows are expected because Ada deliberately owns privacy and authority.

More important is **where the gaps are**:

### ReMe is strongest at

- human-owned Markdown;
- file watching/editing;
- source -> daily -> digest layering;
- compact consolidation;
- explicit source links;
- local lexical/link retrieval;
- current-state deletion/index maintenance.

### ReMe needs Ada semantics at

- trust maturity;
- confirmation basis;
- permission separation;
- protection-domain selection;
- shared minimized derivatives;
- retention classes;
- per-interlocutor vs global personality.

### ReMe has the largest functional gaps at

- deterministic unresolved contradiction lifecycle;
- observed-pattern aging;
- provider-independent external-document references/lifecycle.

None of these gaps currently disqualifies ReMe as a **substrate**, because they sit at boundaries Ada already intends to own. They do, however, argue against exposing ReMe directly as Ada's public Memory model.

## Spike acceptance cases derived from the matrix

When local execution becomes available, the minimal ReMe spike should prove:

1. **Outside edit + clean rebuild**
   - write Memory;
   - stop ReMe;
   - edit Markdown manually;
   - remove/move `metadata/`;
   - restart;
   - verify search and graph use only current files.

2. **Operational forget**
   - ingest and retrieve a fact;
   - delete current Memory;
   - verify immediate retrieval absence;
   - rebuild metadata from scratch;
   - verify it remains absent.

3. **Workspace isolation**
   - run private-A and private-B workspaces;
   - place a unique canary secret in each;
   - verify search/read in A cannot surface B and vice versa;
   - verify no global derived cache contains both.

4. **Correction/contradiction**
   - run explicit correction case;
   - run two ambiguous explicit contradictory statements;
   - observe exactly what Auto Dream writes before adding Ada lifecycle controls.

5. **Local-only model path**
   - Ollama only;
   - network egress disabled;
   - Auto Memory/Dream still works or fails closed with a clear dependency gap.

6. **External document adapter prototype**
   - keep source PDF outside ReMe workspace;
   - materialize/normalize only under Ada control;
   - persist Ada-owned external reference in generated Memory;
   - remove materialized copy and verify summary remains useful.

7. **Resource/maintenance footprint**
   - measure baseline process memory and CPU for one workspace;
   - repeat for multiple concurrent protection-domain workspaces.

## Current interpretation

The scenario matrix **does not overturn ReMe's lead**.

It changes what "adopt ReMe" would mean:

> ReMe should be evaluated as a file-native Memory engine behind an Ada-owned semantic and security adapter, not as Ada's Memory domain model itself.

No dependency or architecture selection is made by this matrix.
