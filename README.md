# Ada

Ada is a local-first, privacy-first personal AI assistant project named after Ada Lovelace.

> **Status:** Initial implementation foundation. PydanticAI is the first replaceable agent-runtime adapter, Ada starts as a Python-first container-first modular monolith, Cedar is implemented behind AdaGuard, DBOS is the accepted durable-execution substrate behind Ada-owned action/outcome semantics, and the first development-only file-native Memory baseline is implemented behind Ada-owned types/ports.

## Vision

Ada should feel like a capable personal companion rather than a developer console: natural voice interaction, persistent user-controlled memory, contextual awareness, and useful computer control — while keeping privacy, transparency, and human control as first-class requirements.

## Personality

Ada is a modern assistant inspired by Ada Lovelace, especially the combination of analytical rigor and imagination associated with her idea of "poetical science". The inspiration is character, not impersonation: Ada does not claim to be the historical person or invent nineteenth-century memories.

The **distribution seed** is a real package asset at `src/ada/bootstrap/default_personality.toml`, so it can be replaced by a fork/distribution without changing Ada's trust architecture.

The intended lifecycle is: **empty Memory -> seed once -> active personality lives in user-controlled Memory**. From then on, personality may gradually learn and evolve while remaining inspectable, editable, reversible, and separate from permissions/privacy/action truth.

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
- **New personal Memory is private by default.** Sharing requires an explicit rule/source audience, and each person's private Memory must eventually be technically isolated rather than merely kept in a different folder.
- **Forgetting is not automatically historical erasure.** Forgetting removes content from what Ada currently reads/searches and from rebuildable derived indexes; older versions/backups may remain until a separate purge policy removes them.
- **Risky authority stays explicit.** Broad or sensitive permissions require an appropriate trusted approval path; the model cannot approve itself.
- **Unknown external outcomes must stay unknown.** If Ada cannot prove whether a consequential external action succeeded, it must reconcile the provider state before retrying rather than risking a duplicate action.
- **Technical success is not the same as real-world success.** A completed phone call does not automatically mean an appointment was booked; Ada should record only what can actually be verified.
- **Memory remains user-controlled.** The authoritative long-term memory is designed to stay outside framework/runtime internals and remain inspectable and editable by the user.

The accepted [Memory architecture](docs/decisions/ADR-0008-memory-architecture.md) is file-native and Markdown-first: current human-editable files are authoritative, private/shared Memory must map to enforceable protection domains, and automatic learning preserves separate dimensions for what knowledge is (for example a preference/fact/routine), how it arose (explicit statement, observed fact, behavioral observation, hypothesis), and its lifecycle/maturity. Promotion into established Memory crosses an Ada-owned validation boundary. **Only `learning/` expires, compacts, or disappears automatically**: observed facts, behavioral observations, hypotheses and non-durable extracts/summaries live there until promoted or compacted. Established `memory/` never disappears automatically; observation-derived `confirmed/observed_pattern` knowledge may be marked `stale` non-destructively, while explicit facts/preferences never become stale merely through time. Facts already owned by calendar/contact/document systems stay source-owned by default. Original documents/raw artifacts live outside Memory in **independently configurable source stores/providers per protection domain**; there is no required central Ada source tree. Existing stable originals are referenced. Directly received files are persisted only when the user asks or retained durable Memory/evidence needs a resolvable original; otherwise they remain session-only, and without a configured destination durable persistence fails closed. Forgetting Memory never changes or deletes an original. Derived RAG/search indexes are rebuildable caches rather than independent truth. Claim/source/lifecycle information stays inspectable without a second drifting claim store, and Memory never grants permission or substitutes for action truth.

The MVP baseline starts with current-file reads and the simplest sufficient local search. Protected vault access is mediated by a **host-side Memory Broker**: Ada requests only the domain(s) needed for the current authorized task instead of holding standing access to every household vault. If RAG/FTS/vector/graph retrieval is added, it remains an automatically rebuildable scoped cache: candidate hits are resolved back to their current authoritative owner (Memory Markdown or the source-owned provider via the broker), lifecycle/maturity/scope are checked, and unavailable-source cached values are only last-known/unverified context. Git-style per-protection-domain history is the leading versioning-adapter candidate once safe edit capture/concurrency/recovery are implemented; Git identity is not authentication. ReMe, LangMem, Hindsight and similar frameworks are optional derived components that must earn their added runtime and maintenance cost. A [synthetic control](research/memory/control/README.md) demonstrates useful baseline behavior and failure modes, but enforceable vault isolation, safe concurrent writes, section-aware current/superseded retrieval, representative recall, and operational forgetting still require implementation validation. The architecture is accepted. A development-only current-file baseline now implements ordinary Markdown Memory/learning files, seed-once personality loading, explicit-vs-observed evidence separation, conservative explicit promotion, and current-state forgetting. The Memory Broker, enforceable household protection domains, encryption, safe Git/versioning concurrency, automatic retention/staleness, and derived retrieval remain unimplemented, so this baseline is **not** approved for real household Memory.

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

This table is intentionally short and user-facing. Detailed trade-offs, versions, evidence, and re-open triggers live in the ADRs and research documents.

The current DBOS-backed calendar path is **synthetic/test-only**. No real calendar account or personal event data is connected yet. Before a production provider is added, Ada must review how sensitive event payloads are stored in durable workflow state and minimize or reference them appropriately.

## Current phase

1. Keep Ada-owned domain and security boundaries independent from replaceable frameworks.
2. Build the smallest representative vertical slice from the confirmed scenarios.
3. Evaluate missing capabilities independently as **reuse / adapt / build**, with an explicit existing-system and license scan before custom implementation.
4. Add stronger process/container isolation only when a capability's risk or lifecycle requires it.
5. Keep authoritative Memory outside the Ada runtime/container.

See the [representative scenarios](docs/product/representative-scenarios.md), [modular core boundaries](docs/architecture/modular-core-boundaries.md), and [backlog](docs/todo.md).

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

By default this development chat still uses the packaged personality seed. To exercise the new file-native baseline deliberately, pass an explicit development Memory root; Ada seeds `memory/personality.md` once and then current file contents win, including manual edits. This path is not a protected household vault yet.

Inside the chat:

- `/reset` clears the current ephemeral session context;
- `/quit` exits.

The model and endpoint remain configurable:

```bash
ada chat --model qwen3.5:9b --ollama-url http://localhost:11434/v1
```

Development-only file-native Memory can be exercised explicitly:

```bash
ada chat --memory-root ./tmp/ada-memory
```

Do not use that unprotected root for real household data. Broker-mediated protection domains, encryption, and safe Git/versioning are separate MVP gates.

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
