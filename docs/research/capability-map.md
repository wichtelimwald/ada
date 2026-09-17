# Ada capability map

**Status:** Discovery — candidates are illustrative, not selected.

| Human metaphor | Capability | Status | Example candidates to research later |
|---|---|---|---|
| Face | Desktop interaction / visual assistant state | Open | Native UI, Tauri, other lightweight desktop approaches |
| Ears | Speech-to-text / wake interaction | Open | whisper.cpp and credible alternatives |
| Voice | Text-to-speech | Open | Kokoro and credible alternatives |
| Brain | Agent orchestration / reasoning | Open | Letta, minimal custom orchestration, other maintained agent runtimes |
| Memory | Persistent personal memory | Open | Letta memory, local Markdown/Obsidian vault, dedicated local store, hybrid approaches |
| Hands | Computer control / actions | Open | Open Interpreter runtime, native OS APIs behind a policy layer, other maintained alternatives |
| Eyes | Screen/camera understanding | Open | To be researched only if product discovery requires it |
| Guard | Policy / permission engine | Open | Must be deterministic; framework choice not made |
| Privacy broker | Optional cloud egress | Open | Architecture to be defined only if cloud use is required |

## Decision order

Do not choose technologies merely to complete the table. Product discovery first defines which capabilities belong in MVP/v1/later. Only then evaluate the relevant rows.
