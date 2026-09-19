# Ada

Ada is a local-first, privacy-first personal AI assistant project named after Ada Lovelace.

> **Status:** Initial implementation foundation. Product scope is confirmed; ADR-0002 selects PydanticAI as the first replaceable agent-runtime adapter and ADR-0003 selects a Python-first, container-first modular monolith.

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
- **KISS / YAGNI.** Prefer existing, maintained components over custom infrastructure when they fit.
- **Evidence before decisions.** Framework choices are researched, compared, and documented before adoption.

## Current phase

1. Keep Ada-owned domain and security boundaries independent from replaceable frameworks.
2. Build the smallest representative vertical slice from the confirmed scenarios.
3. Evaluate missing capabilities independently as **reuse / adapt / build**.
4. Add stronger process/container isolation only when a capability's risk or lifecycle requires it.
5. Keep authoritative Memory outside the Ada runtime/container.

See the [representative scenarios](docs/product/representative-scenarios.md), [modular core boundaries](docs/architecture/modular-core-boundaries.md), and [backlog](docs/todo.md).

## Inspiration and upstream candidates

Mark LIV is a product/UX inspiration only. Its repository is licensed CC BY-NC 4.0; Ada does not copy or derive from its source code or assets.

Potential upstream components such as Open Interpreter, Letta, local speech/model runtimes, Obsidian/Markdown-based memory, ProjectAtlas, and Graphify are **candidates, not dependencies**. Each must be evaluated before adoption.

## Development

Repository language is English. Project discussions with the maintainer are normally in German.

The initial runtime is Python 3.14 with PydanticAI pinned behind an Ada-owned adapter. Development can run through the Dev Container or a local Python environment.

Local validation:

```bash
python -m pip install --editable .
sh scripts/validate.sh
```

Runtime container sanity check:

```bash
docker build --target runtime -t ada:dev .
docker run --rm --cap-drop=ALL --security-opt=no-new-privileges --read-only ada:dev doctor
```

- No direct implementation on `main`.
- No GitHub Actions unless explicitly approved later.
- Non-trivial architecture decisions require an ADR and comparison of alternatives.
- Privacy/security boundary changes require threat-model review.

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and [PRIVACY.md](PRIVACY.md).

## License

Ada's project-owned source code is licensed under the [MIT License](LICENSE). Third-party code, models, assets, and services keep their own licenses and must be reviewed separately before use.
