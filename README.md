# Ada

Ada is a local-first, privacy-first personal AI assistant project named after Ada Lovelace.

> **Status:** Product discovery and architecture exploration. No implementation stack has been selected yet.

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

1. Run the [product discovery interview](docs/prompts/product-discovery-interview-prompt.md).
2. Define MVP / v1 / later scope.
3. Evaluate each capability separately using documented decision matrices.
4. Record significant choices as ADRs.
5. Implement only after the relevant product and architecture decisions are made.

See the [capability map](docs/research/capability-map.md) and [backlog](docs/todo.md).

## Inspiration and upstream candidates

Mark LIV is a product/UX inspiration only. Its repository is licensed CC BY-NC 4.0; Ada does not copy or derive from its source code or assets.

Potential upstream components such as Open Interpreter, Letta, local speech/model runtimes, Obsidian/Markdown-based memory, ProjectAtlas, and Graphify are **candidates, not dependencies**. Each must be evaluated before adoption.

## Development

Repository language is English. Project discussions with the maintainer are normally in German.

- No direct implementation on `main`.
- No GitHub Actions unless explicitly approved later.
- Non-trivial architecture decisions require an ADR and comparison of alternatives.
- Privacy/security boundary changes require threat-model review.

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and [PRIVACY.md](PRIVACY.md).

## License

Ada's project-owned source code is licensed under the [MIT License](LICENSE). Third-party code, models, assets, and services keep their own licenses and must be reviewed separately before use.
