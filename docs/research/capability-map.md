# Ada capability map

**Status:** Discovery — candidates are illustrative, not selected.

The human metaphors below describe **product capabilities, not required software components**. One technology may implement several capabilities, and one capability may require several components. The map must not bias evaluation against integrated approaches such as speech-to-speech systems.

| Human metaphor | Capability | Status | Example candidates to research later |
|---|---|---|---|
| Face | Desktop interaction / visible assistant state | Open | Native UI, Tauri, other lightweight desktop approaches |
| Ears | Speech input / wake interaction | Open | Local and hybrid speech approaches |
| Voice | Speech output | Open | Local and hybrid TTS approaches |
| Brain | Reasoning / orchestration | Open | Stateful agent runtimes, minimal orchestration, integrated models |
| Memory | Persistent personal context | Open | Human-readable local stores, agent memory, dedicated stores, hybrid approaches |
| Hands | Computer control / actions | Open | Permissioned agent runtimes, native OS APIs, other maintained alternatives |
| Eyes | Screen/camera understanding | Open | Research only if product discovery requires it |
| Guard | Policy / permission enforcement | Open | Must be deterministic; implementation not selected |
| Privacy broker | Optional remote/cloud data egress | Open | Define only if remote processing is required |

## Decision order

Do not choose technologies merely to complete the table. Product discovery first defines which capabilities belong in MVP/V1/later. Then evaluate relevant capabilities together with their cross-capability integration constraints.
