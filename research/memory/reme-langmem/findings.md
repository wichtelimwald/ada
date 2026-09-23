# ReMe + LangMem final fit review

- **Status:** Final executable gate pending
- **Date:** 2026-09-23
- **Candidate role split:** ReMe authoritative file substrate + LangMem semantic-change proposal helper
- **Pinned characterization versions:** ReMe 0.4.1.12, AgentScope 2.0.7.post1, LangMem 0.0.30, langchain-ollama 1.1.0

This review narrows the scored ADR-0008 option into the smallest architecture that Ada would actually run.

## 1. ReMe packaging and runtime boundary

### AgentScope is effectively required

ReMe 0.4.1.12 declares AgentScope under the optional `as` extra:

```text
reme-ai[as] -> agentscope[model-ollama]==2.0.7.post1
```

However, ordinary ReMe package bootstrap imports `reme.steps`, and `reme.steps.base_step` imports `agentscope.model.ChatModelBase` at module import time.

Therefore Ada must **not** assume that bare `reme-ai==0.4.1.12` is a usable reduced runtime. The characterized dependency is:

```text
reme-ai[as]==0.4.1.12
```

Do **not** install `reme-ai[core]` for Ada. The core extra additionally pulls capabilities such as Claude/Codex agent SDKs, FAISS, zvec, Neo4j, Polars, Studio, image support, and other integrations that are outside the selected MVP role.

This packaging mismatch is an upstream maintainability concern but not a blocker if ReMe is isolated behind an Ada-owned boundary.

### Do not use ReMe HTTP as Ada's trust boundary

ReMe 0.4.1.12 documents that its HTTP service:

- binds to `127.0.0.1` by default;
- allows CORS from any origin;
- has no general-purpose user authentication;
- can expose jobs that write, move, and delete files.

For Ada, loopback alone is not an acceptable authorization boundary for private household Memory.

### Selected ReMe boundary: stdio MCP subprocess

ReMe's MCP service supports `transport=stdio`; in that mode it does not bind a host/port.

Ada's intended integration is therefore:

```text
Ada / AdaGuard
      |
      | choose allowed protection domain
      v
ReMe subprocess for that vault
      |
      | stdio MCP only
      v
read/search/index over that vault
```

Initial tool allowlist:

- `version`
- `status`
- `search`
- `read`

Not exposed:

- `write`
- `edit`
- `move`
- `delete`
- `auto_memory`
- `auto_dream`

This deliberately prevents ReMe's agent/model workflows from becoming an alternate canonical-write or permission path.

The filesystem/vault remains authoritative. ReMe observes and indexes it.

## 2. LangMem dependency and lifecycle boundary

LangMem 0.0.30 is MIT licensed and storage-agnostic, but its base package has a broader dependency footprint than Ada needs for the selected feature.

Its direct package dependencies include LangChain/LangGraph infrastructure plus provider/observability packages such as:

- `langchain`
- `langchain-core`
- `langchain-openai`
- `langchain-anthropic`
- `langgraph`
- `langgraph-checkpoint`
- `langsmith`
- `trustcall`

Ada uses only the structured Memory-manager path plus `langchain-ollama`.

This is a maintenance/attack-surface cost and is why LangMem remains behind a narrow replaceable port rather than becoming Ada's runtime foundation.

### Security floors

LangMem's own dependency ranges are too broad to serve as Ada's security constraints.

The final characterization enforces at least:

```text
langchain-core >= 1.3.3
langgraph >= 1.0.10,<2
langgraph-checkpoint >= 4.1.1
```

These floors exclude known 2026 unsafe-deserialization ranges.

The final executable run also performs `pip-audit` against the resolved external dependency set and records the exact installed versions.

### No LangGraph persistence for Ada Memory

LangMem is not allowed to introduce a second authoritative Memory store.

For the selected role:

- no LangGraph checkpoint database is authoritative;
- no LangGraph server/auth layer is used;
- no LangSmith service is required;
- no OpenAI/Anthropic provider is used;
- the model endpoint is local Ollama;
- model inputs are minimized typed semantic content, not arbitrary serialized application structures.

## 3. Minimal Ada-owned deterministic boundary

The prior LangMem fixture exposed one critical lesson: when provenance was modeled as an LLM-generated field, LangMem invented a `SESSION_...` value.

The selected architecture removes that capability **by construction**.

LangMem's proposal schema contains only semantic fields:

```text
kind
subject
statement
```

It does not contain:

```text
source/provenance
privacy scope
audience
authority
permission
lifecycle state
validity interval
```

Those remain caller/Ada-owned.

### Explicit correction

Input:

```text
authoritative existing fact
+ new source observation
+ caller-established explicit_correction=true
+ caller-selected correction target
```

LangMem may propose the semantic replacement.

Ada accepts it only if:

- the target is the caller-selected existing memory;
- the subject does not change;
- the proposal matches the explicit correction;
- no extra semantic record is silently introduced.

Ada then attaches the real source references and lifecycle metadata before writing Markdown.

### Non-correction contradiction

When `explicit_correction=false`:

- an existing conflicting explicit claim must not be removed or rewritten;
- a second contradictory claim may be proposed as a new fact;
- Ada assigns the new claim's canonical ID and topic after validating its
  semantic content; model-proposed labels are never authoritative identities;
- Ada owns the resulting `contradicted` lifecycle state;
- a silent overwrite is rejected.

### Authority and scope

LangMem never receives the capability to grant authority or widen Memory scope.

The flow remains:

```text
semantic proposal
      |
deterministic Memory validation
      |
AdaGuard / protection-domain decision
      |
authoritative Markdown write
```

`Memory != Permission` remains unchanged.

## 4. Compatibility with Ada's accepted architecture

### PydanticAI

No replacement.

PydanticAI remains Ada's agent runtime. LangMem is a specialized helper behind an Ada-owned semantic-proposal boundary. ReMe runs out of process.

### DBOS

No overlap.

Memory extraction/validation does not become durable-action truth. Any future durable Memory-maintenance workflow can use DBOS through Ada-owned application semantics if required.

### AdaGuard / Cedar

No replacement.

AdaGuard selects whether a protection domain may be accessed before Ada starts/uses the corresponding ReMe boundary. ReMe does not authorize users.

### Runtime topology

Preferred MVP topology:

```text
Ada Python process
  - PydanticAI
  - DBOS
  - Cedar/AdaGuard
  - LangMem semantic proposal adapter
          |
          | local model
          v
        Ollama

Ada-managed ReMe subprocess
  - AgentScope dependency remains isolated here
  - stdio MCP
  - read/search allowlist
  - one authorized vault boundary at a time
```

A separate LangMem worker is not justified unless the combined dependency test exposes conflicts or future operational evidence demands isolation.

## 5. Supply-chain observations

### ReMe

Positive:

- Apache-2.0;
- PyPI 0.4.1.12 uses Trusted Publishing;
- PyPI provides a GitHub Actions provenance attestation tied to the release commit;
- project is actively maintained.

Concern:

- AgentScope is an effectively required dependency despite being packaged as an optional ReMe extra;
- ReMe pins AgentScope 2.0.7.post1 rather than the newest AgentScope release;
- this requires explicit upgrade review rather than unconstrained updates.

Reviewed AgentScope advisories found for legacy `<=1.0.18` do not include the pinned 2.0.7.post1 version. Separate newer upstream security issues still reinforce the choice to avoid AgentScope tools/MCP-client surfaces that Ada does not need.

### LangMem

Positive:

- MIT;
- source repository remains active and has received 2026 dependency/security maintenance.

Concerns:

- latest published package remains 0.0.30 from 2025;
- PyPI shows a single maintainer and the release was not uploaded through Trusted Publishing;
- package dependencies are broader than the selected semantic-helper role.

Mitigation:

- exact lock/pins in Ada;
- security floors above;
- Dependabot/audit after adoption;
- narrow adapter with no LangGraph persistence or cloud-provider use;
- keep LangMem replaceable.

## 6. Final executable gate

The repository contains:

```text
research/memory/reme-langmem/
  README.md
  config.yaml
  driver.py
  reme_stdio.py
  run.sh
```

The run tests the real combined dependency set:

```text
Ada current package
+ ReMe 0.4.1.12 / AgentScope 2.0.7.post1
+ LangMem 0.0.30
+ langchain-ollama 1.1.0
```

and captures:

- `pip check`;
- exact `pip freeze`;
- `pip inspect`;
- runtime package count/size;
- license metadata inventory;
- security floors;
- `pip-audit`;
- stdio read-only ReMe tool surface;
- valid correction;
- unresolved conflict preservation;
- silent-overwrite rejection;
- caller-owned provenance;
- ReMe recall after accepted write;
- out-of-band Markdown edit -> ReMe re-index.

### First target-Mac run (2026-09-23, head `c63e860`)

The first combined run is **not a pass**. Python 3.14/macOS arm64 preflight,
installation, `pip check`, security floors, and inventory passed. The combined
environment contains 168 distributions (about 397 MiB on disk). `pip-audit`
reported zero known vulnerabilities for the 165 dependencies it listed; this
is point-in-time advisory evidence, not a general safety guarantee. Eleven
license metadata entries require triage; several are obvious scanner false
positives, while LGPL/MPL and unknown metadata need distribution review.

The integration step failed for two independent reasons:

1. Starting `reme start` with an stdio-MCP config sent ReMe Loguru messages to
   **stdout**. The MCP client reported repeated JSON-RPC parse failures. The
   first `Loading config` log is emitted before the application config turns
   off console logging. ReMe 0.4.1.12 already ships
   `reme.components.agent_wrapper.codex_mcp_server`, which resolves config
   without console logs and exposes a selected job list. The second run used
   this upstream bridge and confirmed the clean four-tool MCP surface, but
   exposed a missing index watcher (below).
2. LangMem's non-correction proposal did not pass the preservation validator:
   `Proposal did not preserve one separate 17:00 conflicting claim`. The first
   bundle did not retain the raw proposal, so it cannot distinguish a model
   omission from a schema/validator mismatch. The validator is unchanged.
   The harness now saves both raw proposals before validation and includes
   the integration log tail in the review bundle.

The first run does **not** establish a clean stdio boundary, successful
conflict handling, or authoritative out-of-band reindexing.

### Second target-Mac run (2026-09-23, head `a237359`)

The second combined run is **not a pass**. Preflight, combined installation,
runtime capture, and `pip-audit` passed again, with zero reported vulnerability
records. ReMe started with a clean stdio transport and exposed exactly `read`,
`search`, `status`, and `version`. Initial search for a Markdown fixture was
empty for the entire 45-second wait. LangMem was not reached on this run, so
the unresolved conflict finding from the first run remains open.

The pinned ReMe source identifies the cause: the upstream Codex stdio bridge
removes **all** background and cron jobs from its effective config, including
`index_update_loop`. That job alone runs `init_changes_step` and
`watch_changes_step` for Markdown, dispatching `update_index_step` to populate
the search index. Its absence explains why the prewritten canary never became
searchable.

The research subprocess now resolves config without stdout logging and selects
only the four read tools plus the internal `index_update_loop`. Its MCP service
still exposes exactly the four read tools; the watcher is a non-served
background job. A direct read of the prewritten Markdown is recorded before
the initial search to distinguish file access from indexing on the next run.
The runtime tool-list assertion, proposal validator, and all original gates
remain in place. Rerun the updated spike on the target Mac; this change has
only been checked statically in the development environment.

### Third target-Mac run (2026-09-23, head `f7477f2`)

The third combined run remains **FINDINGS**. Preflight, combined dependency
installation, runtime capture, and `pip-audit` passed (168 distributions; zero
reported vulnerability records). ReMe's stdio service exposed exactly the
four intended read tools. `read` and `search` returned the pre-existing
Markdown, the explicit Thursday correction was validated, and ReMe re-indexed
the Ada-written correction. Out-of-band edit/re-index was not reached.

The saved raw LangMem conflict proposal establishes that the model **did**
preserve the original 16:00 claim unchanged and propose one separate 17:00
claim. It labeled the new claim `pickup-time-17` rather than the canonical
`pickup-time`; the validator previously required an exact subject match and
thus raised `Proposal did not preserve one separate 17:00 conflicting claim`.
This was a validator/schema-boundary mismatch, not evidence of a dropped or
overwritten claim. The first run's identical error cannot be retrospectively
classified because its raw proposal was not captured.

The research validator now accepts only the observed same-topic disambiguation
(`pickup-time-17`) or the exact canonical topic, while requiring exactly two
records, an unchanged existing claim (including kind), and the specific new
17:00 fact. It assigns the new claim Ada's canonical ID `pickup-17` and topic
`pickup-time` before any authoritative write. An unrelated subject or altered
prior claim still fails closed. This fixture is **scenario-specific**, not
proof of a general contradiction resolver. A final target-Mac run must still
pass conflict validation, negative overwrite rejection, and out-of-band
re-indexing before a decision.

### Fourth target-Mac run (2026-09-23, head `be34013`)

The **combined executable characterization passes all of its defined core
steps** on macOS arm64 / Python 3.14.4. The combined Ada + ReMe + LangMem
environment installed with 168 distributions (about 397 MiB). Security floors
and `pip check` passed. `pip-audit` reported zero known vulnerabilities among
the 165 dependencies it listed. ReMe's reported process RSS at the end of the
synthetic integration was 72.38 MiB. This is one point-in-time run, not a
general performance or security guarantee.

The saved integration evidence confirms:

- stdio MCP exposed exactly `read`, `search`, `status`, and `version`; the
  Markdown index watcher remained internal;
- pre-existing authoritative Markdown was readable and searchable;
- LangMem proposed the Thursday correction with no caller-owned provenance
  fields; Ada validated it, attached source references, wrote Markdown, and
  ReMe found the changed text;
- LangMem preserved the 16:00 pickup claim unchanged and proposed a separate
  17:00 fact under the observed `pickup-time-17` label; Ada validated the
  content, mapped it to its own ID/topic, and both files were searchable;
- the synthetic silent-overwrite proposal was rejected;
- after an out-of-band Friday edit, ReMe search and read returned the edited
  Markdown without a model-mediated rewrite.

The last test establishes **file change detection and retrieval**, not
semantic/provenance integrity for arbitrary external edits. Its Friday body
still carries source references for the preceding Wednesday/Thursday history
and no new source for Friday. Ada needs a separate rule for recognizing and
reconciling external edits before treating their metadata as verified. This
run also uses one synthetic vault; it does not implement OS-level protection
or household authorization, even though the earlier ReMe two-workspace canary
test established basic query isolation. The scenario-specific LangMem fixture
does not prove broad learning or contradiction resolution.

### Clarification: the spike duplicates presentation data

The synthetic music note repeats `source_refs` and the superseded Wednesday
statement from YAML in the Markdown body. This makes the test canaries easy to
inspect, but **is not an acceptable production schema**: it creates two places
to update the same item. The target design must choose one canonical location
for each claim and each metadata item; ReMe's search index is only a
rebuildable derivative of those files. A manually edited claim needs no
second YAML provenance record; Ada-extracted claims still need their evidence
visibly associated with the claim they support.

Removing that duplication does not by itself solve the external-edit question.
If the Thursday claim is changed to Friday in the body while its sole YAML
source reference still points to a Thursday source, the reference is stale
even though no field is duplicated. The maintainer clarified the smaller rule
for manual notes: the current file is authoritative, and captured file
revision history is sufficient provenance for a direct edit; claim-level YAML
provenance is not required. The revision must actually be recorded, and its
history alone does not authenticate the editor. A prior source link must not
be presented as proof of the edited claim. Ada-created claims still need
minimized evidence adjacent to the claim in one human-readable unit. The exact
representation and confirmation policy remain open; this is a design finding,
not an added production schema.

### Triage of the 11 flagged license metadata entries

The inventory's substring classifier is a triage tool, not an SPDX parser.
The following checks use the **exact installed versions'** published package
metadata; `cedarpy` is also checked against its release-tagged license file.

| Distribution | Published license / status | Consequence for Ada |
| --- | --- | --- |
| [`psycopg` 3.3.6](https://pypi.org/project/psycopg/3.3.6/), [`psycopg-binary` 3.3.6](https://pypi.org/project/psycopg-binary/3.3.6/) | LGPL-3.0-only | Real redistribution obligation; both are already pulled by the accepted `dbos==3.0.0` (`psycopg[binary]>=3.1`). Review binary wheel content and notices before bundling an installer/container. |
| [`bidict` 0.24.1](https://pypi.org/project/bidict/0.24.1/) | MPL-2.0 | Real file-level copyleft; enters through AgentScope's `python-socketio` dependency. Preserve license/source availability when redistributing. |
| [`certifi` 2026.7.22](https://pypi.org/project/certifi/2026.7.22/) | MPL-2.0 | Real file-level copyleft and certificate-bundle notice/source review if redistributed. |
| [`orjson` 3.12.0](https://pypi.org/project/orjson/3.12.0/) | `MPL-2.0 AND (Apache-2.0 OR MIT)` | Mixed-license source; do not treat the whole wheel as freely selectable MIT-only. Verify bundled notice/source obligations. |
| [`uncalled-for` 0.4.0](https://pypi.org/project/uncalled-for/0.4.0/), [`langmem` 0.0.30](https://pypi.org/project/langmem/0.0.30/), [`beartype` 0.22.9](https://pypi.org/project/beartype/0.22.9/), [`tiktoken` 0.14.0](https://pypi.org/project/tiktoken/0.14.0/) | MIT in published license text | The classifier's weak-copyleft label is a metadata false positive. Normal MIT notice preservation remains. |
| [`json5` 0.15.0](https://pypi.org/project/json5/0.15.0/) | Apache-2.0 for package code; some benchmarks use MIT | The weak-copyleft label is a metadata false positive. Check whether separately licensed benchmark data is present in any redistributed artifact. |
| [`cedarpy` 4.12.0](https://github.com/k9securityio/cedar-py/blob/v4.12.0/LICENSE) | Apache-2.0 in the release-tagged LICENSE; package metadata omits it | Already adopted through ADR-0004 / `NOTICE.md`; this is a metadata gap, not an unknown project license. |

Mozilla's [MPL 2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
explains that MPL files can be combined with differently licensed files while
the MPL obligations stay with those files. This is a **preliminary license
triage**, not a complete binary-wheel/SBOM redistribution audit or legal
sign-off. No newly identified metadata-level hard blocker for Ada's MIT-owned
code is apparent, but LGPL/MPL distribution obligations and notices remain a
hard gate before adoption/packaging. No ReMe/LangMem production dependency has
been adopted by this research PR.

## 7. Current decision gate

The combined executable characterization now passes its defined synthetic
runtime, stdio, semantic, and file-change gates. This closes that experiment,
not the ADR/adoption gates.

The ReMe + LangMem option can move toward ADR selection **only if the final combined run confirms**:

1. Ada + ReMe + LangMem resolve cleanly under Python 3.14;
2. no unresolved high-severity vulnerability exists in the selected dependency graph;
3. transitive license inventory contains no unacceptable dependency for Ada's policy;
4. stdio read-only ReMe boundary works on the target Mac;
5. deterministic proposal validation passes the correction/conflict fixtures;
6. file truth remains authoritative after an out-of-band edit.

The fourth bundle has been reviewed against these six conditions: environment
and semantic/file-change checks pass; the point-in-time vulnerability scan
has zero reported records. The license metadata triage found no immediate
incompatibility, but exact redistributed wheel contents/notices, protection
domain enforcement, external-edit metadata semantics, external-document
reference/lifecycle fit, and independent decision review remain open. Do not
adopt ReMe/LangMem or mark ADR-0008 Accepted on this bundle alone.
