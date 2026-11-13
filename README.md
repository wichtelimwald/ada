# Ada

Ada is a local-first, privacy-first personal AI assistant project named after Ada Lovelace.

> **Status:** Initial implementation foundation. PydanticAI is the first replaceable agent-runtime adapter, Ada starts as a Python-first container-first modular monolith, Cedar is implemented behind AdaGuard, DBOS is the accepted durable-execution substrate behind Ada-owned action/outcome semantics, and the development-only file-native Memory layer now has Ada-owned safe-write/versioning semantics while protected household Memory remains a later gate.

**MVP scope (revised 2026-11-12):** Regular family requests use **email**; a separate **restricted MVP admin chat** sets and changes AdaGuard permissions. The current development chat is not automatically an authorized admin interface. Sender authenticity (beyond the visible `From:` header) must be verified before live effects; implementation belongs to MVP-70. The **immediate milestone is maintaining a family calendar via email** with actual registered household users and deliberately non-sensitive test events, not simulated household identities. General family Memory/learning remains a later MVP increment, and regular interactive chat comes afterward (potential emailed login code/passkey). See the [MVP roadmap](docs/product/mvp-roadmap.md).

## Vision

Ada should feel like a capable personal companion rather than a developer console: natural voice interaction, persistent user-controlled memory, contextual awareness, and useful computer control — while keeping privacy, transparency, and human control as first-class requirements.

## Personality

Ada is a modern assistant inspired by Ada Lovelace, especially the combination of analytical rigor and imagination associated with her idea of "poetical science". The inspiration is character, not impersonation: Ada does not claim to be the historical person or invent nineteenth-century memories.

The **distribution seed** is a real package asset at `src/ada/bootstrap/default_personality.toml`, so it can be replaced by a fork/distribution without changing Ada's trust architecture.

The intended lifecycle is: **empty Memory -> seed once -> active personality lives in user-controlled Memory**. From then on, personality may gradually learn and evolve while remaining inspectable, editable, and recoverable through the same history/edit-capture layer, while staying separate from permissions/privacy/action truth.

See [personality model and lifecycle](docs/product/personality.md).

## Project principles

- **Local first.** Prefer on-device processing where practical.
- **Cloud is optional and explicit.** Remote processing must be visible, minimized, and justified.
- **Privacy by architecture.** Sensitive data must not leak through prompts, logs, telemetry, memory, or tool calls.
- **Least privilege.** Computer control must be mediated by deterministic permissions and approval gates.
- **Untrusted content stays data.** Websites, files, messages, screenshots, retrieved text, tool results, and model outputs must never silently become privileged instructions.
- **User-controlled memory.** Personal memory must be inspectable, editable, exportable, and deletable.
- **Usability matters.** Security and privacy controls must remain understandable and practical.
- **Reuse first / KISS / YAGNI.** Search for existing maintained solutions before designing custom infrastructure; build only when reuse or adaptation does not fit.
- **Evidence before decisions.** Framework choices are researched, compared, and documented before adoption.

## What this means for users

Ada's architecture is deliberately designed so that the AI model is **not** the final authority.

- **Permissions are deterministic.** The model may propose an action, but AdaGuard decides whether it is allowed. Ada reuses the established [Cedar](https://www.cedarpolicy.com/) policy engine instead of inventing a general permission language.
- **Learning does not silently create new rights.** Forwarded text, web pages, files, tool output, model output, or previously successful actions cannot grant Ada additional authority.
- **Private data is not automatically shareable.** Permission to read/store information is separate from permission to disclose it to another person or audience.
- **New personal Memory is private by default.** Sharing requires an explicit rule/source audience, and Ada must enforce trusted actor/audience permissions independently of the model; folder placement is not authorization.
- **Forgetting is not automatically historical erasure.** Forgetting removes content from what Ada currently reads/searches and from rebuildable derived indexes; older versions/backups may remain until a separate purge policy removes them.
- **Risky authority stays explicit.** Broad or sensitive permissions require an appropriate trusted approval path; the model cannot approve itself.
- **Unknown external outcomes must stay unknown.** If Ada cannot prove whether a consequential external action succeeded, it must reconcile the provider state before retrying rather than risking a duplicate action.
- **Technical success is not the same as real-world success.** A completed phone call does not automatically mean an appointment was booked; Ada should record only what can actually be verified.
- **Memory remains user-controlled.** The authoritative long-term memory is designed to stay outside framework/runtime internals and remain inspectable and editable by the user.

The accepted [Memory architecture](docs/decisions/ADR-0008-memory-architecture.md) is file-native and Markdown-first: current human-editable files are authoritative, private/shared Memory uses Ada-enforced logical user/audience scopes (ADR-0012), and automatic learning preserves separate dimensions for what knowledge is (for example a preference/fact/routine), how it arose (explicit statement, observed fact, behavioral observation, hypothesis), and its lifecycle/maturity. Promotion into established Memory crosses an Ada-owned validation boundary. **Only `learning/` expires, compacts, or disappears automatically**: observed facts, behavioral observations, hypotheses and non-durable extracts/summaries live there until promoted or compacted. Established `memory/` never disappears automatically; observation-derived `confirmed/observed_pattern` knowledge may be marked `stale` non-destructively, while explicit facts/preferences never become stale merely through time. Facts already owned by calendar/contact/document systems stay source-owned by default. Original documents/raw artifacts live outside Memory in **independently configurable source stores/providers per protection domain**; there is no required central Ada source tree. Existing stable originals are referenced. Directly received files are persisted only when the user asks or retained durable Memory/evidence needs a resolvable original; otherwise they remain session-only, and without a configured destination durable persistence fails closed. Forgetting Memory never changes or deletes an original. Derived RAG/search indexes are rebuildable caches rather than independent truth. Claim/source/lifecycle information stays inspectable without a second drifting claim store, and Memory never grants permission or substitutes for action truth.

The MVP baseline starts with current-file reads and the simplest sufficient local search. **ADR-0012 changes the MVP security boundary:** Ada must restrict Memory reads, writes, retrieval/context, source access and disclosure by the trusted actor, intended audience and task. S1's logical MemoryBrokerPort contract may be reused in process; a separate host-side Memory Broker, encrypted per-person vaults, Keychain vault keys and VM-to-host IPC are **not MVP requirements**. Mac/device protection, encryption, backups and sync remain the operator's responsibility. Ada does **not** protect local files against other same-user host processes or fully compromised Ada code. A model-facing unrestricted file tool must not bypass scoped Ada APIs.

Derived RAG/FTS/vector/graph indexes remain rebuildable, audience-scoped caches. Candidate hits must be validated against current authoritative Memory or an authorized source provider, and unavailable-source hits are unverified. [ADR-0010](docs/decisions/ADR-0010-memory-write-history.md) accepts current Markdown authority and Git edit history: generic IDs are opaque, corrections use expected revisions, Ada writes serialize, out-of-band edits are captured, and history is never current semantic Memory. Git is not authentication; the last late non-cooperating-save race and executable Git metadata remain open MVP-30 issues. ReMe, LangMem and similar frameworks remain optional, evidence-gated.

The existing development Memory root is **not approved for real household data**, because trusted per-user/audience authorization and full positive/negative data-flow tests have not yet been implemented. It is not an encrypted or OS-isolated household store. Automatic learning and derived retrieval are also still incomplete.

Some of these protections are already implemented; others are architecture rules being implemented incrementally. The project documents accepted decisions separately from work that is still under evaluation.

## Reuse before reinvention

Ada should not build infrastructure merely because it can.

For every substantial capability, the project first checks maintained existing systems, their security/privacy fit, lifecycle cost, integration boundaries, and licenses. Custom code is preferred only when Ada must own a specific trust/domain boundary or existing systems do not fit.

Current examples:

| Capability | Direction | License / status |
| --- | --- | --- |
| Agent runtime | PydanticAI behind an Ada-owned replaceable adapter | MIT; accepted |
| Permissions / authorization | Cedar behind AdaGuard | Apache-2.0; accepted |
| Python Cedar integration | `cedarpy` around the Cedar Rust engine | Apache-2.0; implemented behind AdaGuard |
| Durable external actions / recovery | DBOS behind Ada-owned action/outcome semantics | MIT; accepted by ADR-0005, synthetic calendar slice implemented |
| Local model serving | Self-hosted Ollama with configurable model profile; qwen3.5:9b target-Mac baseline | MIT runtime; model artifact Apache-2.0; accepted by ADR-0006 |
| Development Memory history | Ada-owned file adapter using a separately installed Git CLI | Git is GPLv2 and not vendored by Ada; accepted by ADR-0010 |
| Calendar integration | Standard CalDAV via a small Ada-owned adapter with provider profiles (IONOS Mail Business first), using `icalendar` and `recurring-ical-events` | BSD-2-Clause / LGPL-3.0-or-later; accepted by ADR-0009, read, create, update and cancel implemented (S1-S4) |

This table is intentionally short and user-facing. Detailed trade-offs, versions, evidence, and re-open triggers live in the ADRs and research documents.

The current DBOS-backed calendar path is still **synthetic/test-only in the running application**. The generic CalDAV adapter implements list/create/update/cancel but has only been tested against the in-process IONOS fake server; it is **not** connected to the Ada CLI or to real family data. Update/cancel use approved event versions; recurring events and events with attendees remain read-only. MVP-60 S5 adds availability-only conflict checks and configured approximate travel times (with explicit unknowns). S6 has started with a strict non-secret IONOS configuration loader and a macOS Keychain credential reader ([local setup](docs/setup-caldav-development.md)). This composes an adapter **without contacting IONOS**, but does not itself authorize or prevent calls to its write methods. No live calendar operations are enabled in the Ada runtime: trusted calendar selection, provider privilege cross-checks, D5 durable-state cleanup, real-provider acceptance, and later email/admin-grant integration are still required. **Do not use real household appointments in this development path.**

**Accepted; partially implemented:** [ADR-0009](docs/decisions/ADR-0009-calendar-provider-integration.md) connects calendars through standard CalDAV with one small Ada-owned adapter; differences between providers are described as configuration profiles, and IONOS Mail Business is the first provider. Ada would have its **own** mailbox holding one calendar per family member plus one family calendar; Ada shares each family member's calendar and the family calendar read-only with that person's own mailbox in the same IONOS contract, where it appears automatically in their calendar apps; changes go through Ada. Ada never stores a family member's password, and Ada's password is never set up on family devices. For the MVP this deliberately trades separate accounts for simplicity: all family calendars sit in Ada's account, and Ada's own rules decide who may see which details in chat or email. Ada only knows appointments that are in its calendars, and in the MVP only people with a mailbox in the same IONOS contract can see them. Further CalDAV providers can be added as configuration profiles and other calendar protocols as separate adapters; a stricter per-person setup remains possible later.

## Current phase

Ada now follows a persistent [MVP execution roadmap](docs/product/mvp-roadmap.md).
It defines the work-package order, dependencies, parallelizable steps and the
contract for "next step" / "overnext step" requests. Detailed implementation
gates remain in the [backlog](docs/todo.md), and each non-trivial package gets a
step-level plan under [docs/plans/](docs/plans/).

Current execution principles:

1. Keep Ada-owned domain and security boundaries independent from replaceable frameworks.
2. Implement the next ready MVP work package, or an explicitly requested later ready package, without bypassing dependencies.
3. Evaluate missing capabilities independently as **reuse / adapt / build**, with an explicit existing-system and license scan before custom implementation.
4. Add stronger process/container isolation only when a capability's risk or lifecycle requires it.
5. Keep authoritative Memory outside the Ada runtime/container.

See the [representative scenarios](docs/product/representative-scenarios.md), [MVP roadmap](docs/product/mvp-roadmap.md), [modular core boundaries](docs/architecture/modular-core-boundaries.md), and [backlog](docs/todo.md).

## Inspiration and upstream candidates

Mark LIV is a product/UX inspiration only. Its repository is licensed CC BY-NC 4.0; Ada does not copy or derive from its source code or assets.

Potential upstream components such as Open Interpreter, Letta, local speech/model runtimes, Obsidian/Markdown-based memory, ProjectAtlas, and Graphify are **candidates, not dependencies**. Each must be evaluated before adoption.

## Development

Repository language is English. Project discussions with the maintainer are normally in German.

The initial runtime is Python 3.14 with PydanticAI pinned behind an Ada-owned adapter, Cedar/cedarpy pinned behind AdaGuard, and DBOS pinned behind Ada's durable-action port. Development can run through the Dev Container or a local Python environment.

The first local-chat profile uses a separately installed, self-hosted Ollama service. This baseline is **accepted** by [ADR-0006](docs/decisions/ADR-0006-local-model-runtime.md) after target-Mac validation with qwen3.5:9b.

Local validation from the repository root:

```bash
cd "$(git rev-parse --show-toplevel)"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --editable .
sh scripts/validate.sh
```

The default validation output is intentionally concise. For per-test output, run:

```bash
ADA_TEST_VERBOSE=1 sh scripts/validate.sh
```

A project-local virtual environment is intentional. Do not bypass a Homebrew/PEP 668 externally-managed Python with `--break-system-packages`.

### First local chat

Install Ollama separately, then fetch the current target-Mac baseline model:

```bash
ollama pull qwen3.5:9b
```

With the local Ollama service running:

```bash
ada chat
```

The first local-chat profile only accepts a loopback Ollama endpoint. Conversation history is kept in memory for the current process only and is **not** Ada Memory.

On macOS, run this initial chat **natively** alongside the separately installed
Ollama service, with Ollama bound to host loopback. Use the default bridged Dev
Container for development and tests; it cannot reach the Mac's loopback-only
Ollama service. Ada disables ambient proxy discovery for both readiness and
model requests. This first chat path runs with the macOS user's permissions;
it is not isolated by a runtime container. Containerized local chat needs a
separately reviewed, restricted Ollama connection before it is supported.

By default this development chat still uses the packaged personality seed. To exercise the new file-native baseline deliberately, pass an explicit development Memory root; Ada seeds `memory/personality.md` once and then current file contents win, including manual edits. This is a development-only path without household actor/audience authorization.

Inside the chat:

- `/reset` clears the current ephemeral session context;
- `/quit` exits.

The model and endpoint remain configurable:

```bash
ada chat --model qwen3.5:9b --ollama-url http://localhost:11434/v1
```

Development-only file-native Memory can be exercised explicitly. This path now requires a separately installed `git` CLI and a **dedicated Memory root**. Ada creates and marks its own local history repository inside that root; it refuses to reuse a pre-existing foreign Git repository. Normal Memory reads use only the current Markdown files.

```bash
ada chat --memory-root ~/ada-memory-dev
```

Do not use that development root for real household data: trusted identity/audience scoping and end-to-end permissions are not implemented yet. Ada does not provide per-person vault encryption or same-user Mac process isolation for the MVP; Git history can retain corrected or forgotten content until a separate purge operation.

This first chat milestone does not execute calendar actions. Calendar-create requests are represented as a **non-executable typed draft**. Ada-owned deterministic logic decides which fields are required and checks whether the draft's date, times, and target calendar occur in supported forms in the **current user message**. This is a conservative text check, not proof of user intent: it cannot reliably assign values to different events or interpret corrections and negations. A complete draft is neither authorization nor an executable proposal. Any future conversion into a proposal must address those limits and follow the AdaGuard + durable-action path.

For now, supply the complete event in one message: title, full date including
year, start and end times, and target calendar. When Ada asks for missing details,
repeat the complete request with those details added. Conversation history is
available to the model, but is not authoritative evidence for this check.
Multi-turn draft clarification is not implemented; durations are not converted
into end times, and no default calendar is assumed.

Use 24-hour `HH:MM` for calendar times in this temporary guard. Only
explicit `HH:MM` source text is corroborated here; dotted times, AM/PM,
day-period wording and other natural-language temporal forms remain unresolved,
so Ada asks for the complete event again instead of guessing. Natural-language
time interpretation belongs to the accepted context-aware interpretation
architecture in [ADR-0007](docs/decisions/ADR-0007-context-aware-interpretation.md),
not to a growing regex grammar in the calendar guard.

Runtime container sanity check:

```bash
docker build --target runtime -t ada:dev .
docker run --rm --cap-drop=ALL --security-opt=no-new-privileges --read-only ada:dev doctor
```

- No direct implementation on `main`.
- No GitHub Actions unless explicitly approved later.
- Non-trivial architecture decisions require an ADR, a credible existing-system scan, and license/distribution review.
- Privacy/security boundary changes require threat-model review.

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and [PRIVACY.md](PRIVACY.md).

## License

Ada's project-owned source code is licensed under the [MIT License](LICENSE). Third-party code, models, assets, and services keep their own licenses and must be reviewed separately before use. The initial release plan is source plus a Dockerfile for users to build locally; publication of an Ada-built image/installer requires a separate review of its actual included dependencies and license obligations. See [NOTICE.md](NOTICE.md) for the existing transitive-license findings.
