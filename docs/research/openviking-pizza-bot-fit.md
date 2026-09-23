# OpenViking and Pizza Bot fit for Ada

- **Status:** Research reference
- **Date:** 2026-09-23
- **Purpose:** Evaluate whether OpenViking or Pizza Bot should materially change Ada's current Memory/runtime direction.

This review is intentionally reuse-first. It distinguishes:
- whole-framework adoption;
- component reuse;
- architecture/design reference;
- benchmark-only value.

## OpenViking

### What fits Ada unusually well

OpenViking is no longer just a generic RAG reference. Its current architecture overlaps materially with Ada's Memory requirements:

- agent-native virtual filesystem with `viking://` URIs;
- human-readable memory files and directory structure such as `profile.md`, `identity.md`, `preferences/`, `entities/`, `events/`, `cases/`, `trajectories/`, and `experiences/`;
- separation of resources, memories, skills, and sessions;
- hierarchical L0/L1/L2 context loading;
- session commit -> asynchronous memory extraction/update;
- memory-diff/audit artifacts for committed sessions;
- `find/search/read/write/edit/forget/reindex` style lifecycle operations;
- account/user/peer identity scopes;
- tenant-aware filesystem and retrieval filtering;
- opt-in shared-resource ACLs;
- local storage and local vector backend options;
- API-key/trusted-gateway authentication;
- optional at-rest encryption.

The user/peer split is especially relevant to Ada's per-interlocutor adaptation. It is closer to Ada's privacy model than a single global memory namespace.

### Important mismatches

#### License hard gate

The main OpenViking project/runtime/server is now **AGPL-3.0**.

Under Ada's current permissive/MIT distribution strategy, the main server does not pass the licensing gate.

OpenViking deliberately keeps some client-facing components permissive:
- Rust/CLI: Apache-2.0;
- examples: Apache-2.0;
- some integration examples/plugins retain permissive licenses.

That makes OpenViking useful as:
- a design reference;
- an external benchmark;
- a source of individually permissive client/integration patterns.

It does **not** currently justify making the AGPL server a required Ada runtime dependency.

A separately installed/network service might have different legal implications from linking/bundling, but that would require explicit legal/license review and would still conflict with Ada's current "permissive dependencies by default" strategy.

#### Virtual filesystem vs Ada-owned ordinary vaults

OpenViking exposes filesystem-like semantics, but the authoritative surface is mediated through its server/storage layer and indexed context database.

That is not the same requirement as:

```text
ordinary Markdown/YAML files
owned by the user
directly editable with an ordinary editor
Ada/retrieval indexes disposable and rebuildable
```

OpenViking can read/write/export files and has a local filesystem backend, but Ada should not assume arbitrary out-of-band edits to the backing storage are a supported authoritative workflow without explicit characterization.

#### Scope semantics are close but not identical

OpenViking has strong account/user/peer isolation and shared-resource ACLs.

Ada additionally requires distinctions such as:

```text
Person != Data Subject != Audience != Authority
```

and private -> shared minimized derivatives.

OpenViking's identity/scoping model is useful reference material, but cannot replace AdaGuard or Ada's household-sharing semantics automatically.

#### Semantic lifecycle still needs characterization

OpenViking supports memory extraction, updates, experiences, cases, trajectories, and session memory diffs. That is promising.

However, this review did not establish Ada's exact lifecycle:

```text
observed -> provisional -> confirmed -> stale / contradicted / superseded
confirmation_basis = explicit_user | observed_pattern
```

Nor did it prove Ada's explicit-correction vs unresolved-contradiction semantics.

### OpenViking assessment

**Whole-framework adoption:** blocked by current license strategy.

**Memory architecture relevance:** high.

**Component reuse:** possible only for individually permissive components after license/dependency review.

**Best role now:** strong design/benchmark reference, especially for:
- hierarchical context loading;
- user/peer scope;
- session -> memory extraction;
- resource/memory/skill separation;
- memory audit/diff;
- tenant-aware retrieval.

Do not add the AGPL server to Ada's dependency graph unless the license strategy is explicitly reopened.

---

## Pizza Bot

### What it actually is

Pizza Bot is a local-first application/runtime for long-running agent work, developed at Amazon and released under Apache-2.0.

Its architecture is:
- TypeScript / Node >=24;
- DeepAgents + LangGraph runtime;
- HTTP/SSE protocol boundary;
- Electron/web/CLI clients;
- SQLite checkpoints, long-term store, and application state;
- Skills and MCP plugins;
- background/durable runs;
- cron and webhook triggers;
- Human-in-the-Loop approval pauses;
- explicit local-folder grants;
- Ollama and several cloud model providers.

This makes Pizza Bot much more relevant to Ada's **runtime/control-plane UX** than to Ada's authoritative Memory backend.

### Strong Ada-aligned ideas

#### Durable work + reconnect

Runs continue when the client disconnects and can be replayed/resumed.

That matches Ada's eventual need for:
- asynchronous work;
- email/calendar tasks that outlive a UI request;
- interrupted/resumed interactions;
- a visible queue of completed work and pending decisions.

Ada already selected DBOS for durable action/outcome semantics, so Pizza Bot is better treated as a pattern/benchmark than a second durable runtime.

#### HITL / approval UX

Pizza Bot uses native LangGraph interrupts and surfaces durable approval requests in an Action queue.

This is highly relevant UX reference material for Ada's:
- explicit approval requests;
- risk-sensitive actions;
- delayed user response;
- resumable workflows.

However, Pizza Bot's interrupt/approval mechanism is **not equivalent to AdaGuard**.

AdaGuard owns authority and policy. A runtime HITL pause can present/collect approval, but must not become the policy engine.

#### Filesystem grants

Pizza Bot gives no default home-directory access. Users explicitly grant folders, read-only by default, and write access is separate.

It additionally validates canonical paths and rejects traversal/symlink escape patterns.

This is a strong pattern for Ada's future local-file capability.

#### Runtime boundary discipline

Pizza Bot deliberately confines DeepAgents/LangGraph construction to one production package and keeps frontend/protocol projections outside that runtime.

That strongly validates Ada's existing decision to keep PydanticAI replaceable behind Ada-owned interfaces.

### Important mismatches

#### Full runtime adoption would reverse accepted Ada decisions

Ada already has:
- PydanticAI behind an Ada-owned runtime boundary;
- Python-first modular monolith;
- DBOS durable execution;
- Cedar/AdaGuard authorization.

Adopting Pizza Bot wholesale would introduce:
- a second language/runtime (Node/TypeScript);
- LangGraph/DeepAgents as the central agent runtime;
- LangGraph checkpoint/store semantics alongside DBOS;
- a second approval/control mechanism.

That would increase architecture surface rather than reuse it.

#### Memory is not Ada's required authoritative model

Pizza Bot persists:
- `checkpoints.sqlite`;
- `store.sqlite` for long-term memory;
- `app.sqlite`;
- a `memories/` directory.

Its architecture explicitly uses LangGraph's store for cross-thread long-term memory.

Therefore it does not directly solve Ada's primary Memory requirement: ordinary human-owned Markdown/YAML as the authoritative source with derived indexes disposable.

#### Household security semantics are not built in

Pizza Bot has useful local folder grants and remote bearer auth, but it is primarily a single-backend/local-user application.

It does not provide Ada's household/person/data-subject/audience/authority model.

#### Young public project

Pizza Bot was only recently released publicly, despite substantial internal Amazon use.

Current open issues include checkpoint growth (reported 1.24 GB for 32 threads), which is directly relevant to Ada's concern about durable-state growth.

### Pizza Bot assessment

**Whole-framework adoption:** poor fit with already accepted Ada architecture.

**Memory backend:** weak fit.

**Component/code reuse:** limited by TypeScript/LangGraph coupling; evaluate only if a component is independently useful and dependency-light.

**Architecture-pattern value:** high, especially:
- durable "Unread / Action" UX;
- approval/resume protocol;
- explicit folder grants;
- runtime/protocol separation;
- skills/subagent capability boundaries;
- cron/webhook-triggered long-running work.

---

## Side-by-side Ada relevance

| Area | OpenViking | Pizza Bot |
| --- | --- | --- |
| License fit | **FAIL for main server (AGPLv3)** | **PASS (Apache-2.0)** |
| Authoritative human-readable Memory | **Close conceptually, but mediated VFS must be characterized** | **Weak: SQLite store is central** |
| Memory extraction/evolution | **Strong / worth benchmarking** | Moderate, runtime-oriented |
| User/person scoping | **Strong user/peer model** | Limited for Ada household semantics |
| Retrieval/context loading | **Strong** | Mostly LangGraph/runtime store |
| Local-first | Strong | Strong |
| Local Ollama | Supported | Supported |
| HITL / approvals | Not its main differentiator | **Strong architecture reference** |
| Durable/background work | Sessions/async processing | **Strong** |
| Local filesystem grants | Context filesystem, ACL/auth | **Strong explicit-grant model** |
| Fit with accepted PydanticAI runtime | External memory service possible, but license blocks current path | Whole runtime conflicts |
| Fit with DBOS | Separate context role possible | Significant overlap |
| Direct adoption under current Ada constraints | **No** | **No** |
| Keep as reference | **Yes — Memory/context benchmark** | **Yes — runtime/HITL/UX benchmark** |

## Recommendation for current research

Do not expand the executable four-way Memory benchmark to six full candidates.

Instead:

1. keep ReMe, LangMem, Hindsight, and Letta as the executable Memory candidates;
2. keep **OpenViking** as a high-value architecture/semantic benchmark but license-blocked implementation candidate;
3. extract concrete OpenViking benchmark scenarios into the decision matrix:
   - hierarchical L0/L1/L2 recall;
   - user vs peer memory;
   - session commit/memory diff;
   - resource/memory separation;
4. keep **Pizza Bot** out of the Memory score;
5. add Pizza Bot patterns to future runtime/HITL/filesystem-capability research:
   - durable Action queue;
   - approval/resume;
   - explicit read/write folder grants;
   - protocol/runtime seam;
   - background cron/webhook tasks.

The key reuse-first conclusion is:

```text
OpenViking: technically very relevant, license-blocked as Ada core dependency.
Pizza Bot: architecturally very relevant, but for runtime/HITL patterns rather than Memory.
```

Neither finding creates a reason to implement more Ada-specific machinery now.
