# Ada

Ada is a local-first, privacy-first personal AI assistant project named after Ada Lovelace.

> **Status:** Initial implementation foundation. PydanticAI is the first replaceable agent-runtime adapter, Ada starts as a Python-first container-first modular monolith, Cedar is implemented behind AdaGuard, and DBOS is the accepted durable-execution substrate behind Ada-owned action/outcome semantics.

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
- **Risky authority stays explicit.** Broad or sensitive permissions require an appropriate trusted approval path; the model cannot approve itself.
- **Unknown external outcomes must stay unknown.** If Ada cannot prove whether a consequential external action succeeded, it must reconcile the provider state before retrying rather than risking a duplicate action.
- **Technical success is not the same as real-world success.** A completed phone call does not automatically mean an appointment was booked; Ada should record only what can actually be verified.
- **Memory remains user-controlled.** The authoritative long-term memory is designed to stay outside framework/runtime internals and remain inspectable and editable by the user.

The proposed [Memory architecture](docs/decisions/ADR-0008-memory-architecture.md) treats direct Markdown edits as authoritative file content. Captured file history is sufficient provenance for those manual edits; Ada should not require duplicate claim metadata in YAML or infer who edited a file. The versioning mechanism and Memory backend are still under evaluation.

The maintainer-confirmed **proposed MVP path** starts with Markdown, simple current-file search and per-domain Git history once actual edit capture is verified. ReMe and LangMem are optional candidates that must earn their added runtime and maintenance cost. A [small synthetic control run](research/memory/control/README.md) confirms current-file search and Git diff detection, but automatic edit capture, exclusion of forgotten content from future derived indexes, enforceable private vaults, and representative recall remain open. The proposal is not an accepted backend or an implemented Memory service.

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

For local chat in a container on macOS, select the separate
`.devcontainer/local-chat/devcontainer.json` profile or run the runtime image
with Docker Desktop host networking enabled (Docker Desktop 4.34+):

```bash
docker build --target runtime -t ada:dev .
docker run --rm -it --network=host --cap-drop=ALL \
  --security-opt=no-new-privileges --read-only --tmpfs /tmp:rw,noexec,nosuid \
  --pids-limit=256 ada:dev chat
```

Keep Ollama bound to host loopback. Ada bypasses proxy settings for both its
readiness check and model requests. Host networking allows the container to
reach **other host services too** and cannot be used with Docker Desktop's
Enhanced Container Isolation; this opt-in profile is for reviewed development
code, without private Memory or secrets mounted. If unavailable, use native
local chat rather than exposing Ollama on all interfaces.

The development profile uses a read-only container root with temporary
home and /tmp; editor extensions stored in the container home do not survive
a rebuild. The repository bind mount remains writable for development;
Python imports the mounted `/workspace/src` so edits take effect without a
rebuild. The host-network profile runs no repository setup script automatically.
Review the checkout before running commands in it; use the default development
profile for routine validation. Rebuild the image when dependencies or package
metadata change.

Until the authoritative Memory backend is selected, this development chat temporarily falls back to the packaged personality seed. Once Memory is wired, the seed is used only when Memory has no personality yet; existing Memory always wins.

Inside the chat:

- `/reset` clears the current ephemeral session context;
- `/quit` exits.

The model and endpoint remain configurable:

```bash
ada chat --model qwen3.5:9b --ollama-url http://localhost:11434/v1
```

This first chat milestone does not execute calendar actions. Calendar-create requests are first represented as a **non-executable typed draft**. Ada-owned deterministic logic — not the model — decides which material fields are actually required and checks them against the original user request, so model-invented requirements or silently invented dates cannot become action requirements. Until a provider/default-calendar policy is explicitly defined, the target calendar remains a required material field rather than being guessed. Only a later deterministic application step may turn a complete draft into an action proposal; proposals then follow the existing AdaGuard + durable-action path rather than giving the model direct privileged tools.

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
