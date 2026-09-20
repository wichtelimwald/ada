# Ada

Ada is a local-first, privacy-first personal AI assistant project named after Ada Lovelace.

> **Status:** Initial implementation foundation. PydanticAI is the first replaceable agent-runtime adapter, Ada starts as a Python-first container-first modular monolith, Cedar is implemented behind AdaGuard, and DBOS is the accepted durable-execution substrate behind Ada-owned action/outcome semantics.

## Vision

Ada should feel like a capable personal companion rather than a developer console: natural voice interaction, persistent user-controlled memory, contextual awareness, and useful computer control — while keeping privacy, transparency, and human control as first-class requirements.

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

Local validation from the repository root:

```bash
cd "$(git rev-parse --show-toplevel)"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --editable .
sh scripts/validate.sh
```

A project-local virtual environment is intentional. Do not bypass a Homebrew/PEP 668 externally-managed Python with `--break-system-packages`.

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

Ada's project-owned source code is licensed under the [MIT License](LICENSE). Third-party code, models, assets, and services keep their own licenses and must be reviewed separately before use.
