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
| 3 | Correction | **PARTIAL / ADAPTER REQUIRED** | Independent runs differ: one produced contradictory generated metadata/digest text, while the later comparison run kept body and description consistently Thursday. Correction works operationally, but model-generated consolidation is not deterministic enough to define canonical truth. |
| 4 | Contradiction | **PARTIAL / ADAPTER REQUIRED** | Executable review showed ReMe preserved two conflicting claims separately and did not last-write-win, but it created no deterministic contradiction relation/state. Ada must own that relation. |
| 5 | Private/shared scope | **ADA-OWNED + CHARACTERIZE** | One ReMe workspace can plausibly map to one protection domain. Ada must choose which workspaces are accessible and create permitted minimized shared derivatives. |
| 6 | Provenance after source deletion | **ADAPTER** | Digest nodes retain source links, but source deletion/lifecycle semantics are not Ada's minimized non-resolvable provenance contract. Need source-ref degradation behavior. |
| 7 | Forget | **NATIVE / CHARACTERIZE** | Current-file deletion is watched and derived index entries are pruned. Must prove forgotten content does not return after full metadata rebuild. |
| 8 | No authority from learning | **ADA-OWNED** | ReMe is not an authorization engine. AdaGuard remains mandatory. |
| 9 | No archive rescan | **ADA-OWNED / ADAPTER** | ReMe retains session source by default. Ada must control whether/when session material may be reprocessed after a deliberate forget. |
| 10 | Offline recall | **NATIVE / CHARACTERIZE** | BM25 and explicit-link retrieval are local and do not require a cloud LLM. End-to-end Ada local configuration still needs testing. |
| 11 | Gardening | **ADAPTER** | Auto Dream consolidates/refines/corrects automatically. Ada requires inspectable/confirmable destructive or material restructuring, so policy and proposal mode must wrap it. |
| 12 | Preference learning | **PARTIAL / ADAPTER** | Explicit preference was preserved with provenance and digested successfully, but ReMe promoted it into model-generated 'binding' wording without Ada's subject/scope/maturity contract. |
| 13 | Routine learning | **ADAPTER** | ReMe can consolidate recurring procedures/patterns; Ada must own maturity and ensure routine never becomes authority. |
| 14 | Learning correction | **PARTIAL / ADAPTER REQUIRED** | Explicit correction works operationally. One run inverted derived text; a later run corrected consistently but Auto Dream integrated 0/3 extracted units because of receipt validation failures. ReMe-derived narratives cannot define Ada truth. |
| 15 | Pattern aging | **GAP / ADAPTER** | No matching category-specific observed-pattern aging state was found. ReMe can use dates/search but does not expose Ada's `stale` lifecycle. |
| 16 | Contradictory explicit statements | **PARTIAL / ADAPTER REQUIRED** | Both claims survived separately and were not treated as correction, but no first-class unresolved `contradicted` state linked them; Dream conflict consolidation was skipped. |
| 17 | Explicit correction | **OPERATIONAL PASS / SEMANTICALLY NON-DETERMINISTIC** | Both runs updated the source note to Thursday. One run produced contradictory derived text; the later run kept generated description consistent. The model-driven derived layer is therefore not reliable enough to be canonical without external validation. |
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

### Executable semantic integrity finding

ReMe's generated derived text is **not internally authoritative** enough for Ada, but the exact failure is not deterministic:

- the first semantic run produced disagreement between corrected source/body and generated description/digest text;
- the later four-candidate run corrected Wednesday -> Thursday consistently in the source note and description, so the earlier inversion did **not** reproduce;
- that later Auto Dream run extracted three plausible units but integrated 0/3 because the agent receipts failed validation;
- unresolved conflicting claims were preserved separately in both runs but not linked by a deterministic contradiction object.

Therefore the conclusion is not "ReMe always corrupts corrections". The supported conclusion is narrower: model-generated consolidation varies across runs and requires an authoritative semantic/provenance boundary outside ReMe before derived text can influence canonical recall.

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

## Executable characterization status

The macOS/Python-3.14 spike has now provided direct evidence for several scenarios:

| Scenario | Executable result | Remaining question |
| --- | --- | --- |
| #2 Outside edit | **PASS** | none for basic file -> clean metadata rebuild path |
| #7 Forget | **PASS** | Git/history purge remains deliberately separate |
| #10 Offline recall/local operation | **PASS** | tested with local BM25/file retrieval and local Ollama Memory flow |
| #12 Preference learning | **OPERATIONAL PASS** | inspect resulting maturity/provenance semantics |
| #14 Learning correction | **OPERATIONAL PASS** | inspect resulting supersession/confirmation semantics |
| #16 Contradictory explicit statements | **OPERATIONAL PASS** | inspect whether conflict remains unresolved vs model reconciliation |
| #17 Explicit correction | **OPERATIONAL PASS** | inspect exact old/new lifecycle representation |
| #18 Private vault isolation | **PASS for two-workspace canary isolation** | Ada still owns authorization, encryption, and federated retrieval |
| #24 Conversation continuity pipeline | **OPERATIONAL PASS** | inspect summary/digest quality and transcript-retention fit |

The complete native-Ollama characterization also passed a direct Qwen3.5 tool-call probe and the full Auto Memory -> Auto Dream sequence.

"Operational PASS" intentionally means the mechanism completed without runtime failure. It does not promote ReMe's model-generated semantics to Ada authority.

## Current interpretation

The scenario matrix **does not overturn ReMe's lead**.

It changes what "adopt ReMe" would mean:

> ReMe should be evaluated as a file-native Memory engine behind an Ada-owned semantic and security adapter, not as Ada's Memory domain model itself.

No dependency or architecture selection is made by this matrix.
