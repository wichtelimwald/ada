# ADR-0012: User- and audience-scoped Memory access for the MVP

- **Status:** Accepted (MVP boundary; implementation not yet validated)
- **Date:** 2026-11-12
- **Accepted:** 2026-11-12
- **Supersedes:** ADR-0008's MVP requirements for OS-enforced private vaults, a separate host-side Memory Broker and encryption, plus proposed ADR-0011. Other ADR-0008 Memory decisions remain accepted.

## Context

Product discovery requires Ada to use and disclose only information relevant to and authorized for the acting user and intended audience. It does not require Ada to implement macOS storage encryption or protect unlocked local files against other applications of the same logged-in user.

The later host-side broker, per-person encrypted vault, Keychain and container-to-host IPC topology expanded the threat model beyond that MVP scope. The maintainer explicitly clarified on 2026-11-12 that Mac-level data protection is not Ada's responsibility. Private/shared **Ada-level data access** remains essential.

## Decision

1. **Enforce scope in trusted Ada code.** A trusted actor identity, audience, authorization and task/operation determine allowed private and shared data. AdaGuard/application logic validates this independently of the model, before reads, retrieval, writes and disclosure. Missing or ambiguous scope fails closed.
2. **No model-granted authority.** Model output, prompts, untrusted documents, search results, raw paths and caller-selected domain IDs cannot grant or widen access. Do not expose unrestricted filesystem/source-provider tools to model-driven paths. A minimal shared derivative such as busy time requires explicit permission and must not reveal private details.
3. **Reuse, do not assume a service.** MVP-30 S1's MemoryAccessContext and MemoryBrokerPort are useful logical scoping/test contracts, not authorization tokens or evidence that an extra host process is necessary. Prefer the simplest trusted in-process adapter/service after examining existing AdaGuard and Memory paths. Do not prematurely implement another policy engine, IPC system or vault provider.
4. **Maintain user-owned authoritative data.** Markdown-first, human-editable Memory, correction/forget semantics, Git recovery history, independently configurable source/document providers and private-by-default logical scopes remain. Indexes/caches cannot recombine or leak unauthorized contexts. Git and directory names are not authorization.
5. **No Ada-managed host security in the MVP.** Ada does not need per-person encrypted images, Keychain vault passwords, separately encrypted Git stores, dedicated macOS user or daemon, container-to-host broker IPC, or OS-level same-user isolation. The operator is responsible for Mac accounts, optional FileVault, device protection, backup and sync. This is not a claim that those protections are actually configured.
6. **Preserve other security requirements.** Least privilege, secrets exclusion, prompt-injection resistance, data minimization, explicit remote disclosure, deterministic Memory write validation, safe file/history access, current-only retrieval, and historical forgetting distinctions remain unchanged.

## MVP channel identity (clarification 2026-11-12)

The **only family-facing MVP channel is email**. Map a registered sender address to a configured actor only after the inbound channel supplies credible authentication evidence; a visible `From:` header or forwarded sender name alone is not proof. Authentication and reply/recipient checks are owned by MVP-70, not by the Memory store. The intended audience comes from trusted configuration and the actual mail-routing context, never merely from quoted content or a recipient string that could expand access. Unknown or unverified senders receive no private Memory. AdaGuard decides what that verified actor may read or approve.

The existing native local-chat CLI stays a development/test harness. Later family-facing chat may use an emailed one-time login code and/or a passkey; the exact authentication and session design is deferred. This does not authorize general/high-impact permission grants through ordinary email; higher-assurance approval requirements must be resolved explicitly or held out of MVP scope.

## Explicit trade-off / residual risk

Ada's authorization is an **application behavior guarantee**, not a separate host-process security boundary. Other applications of the same macOS user — or compromised Ada code/dependencies with its filesystem rights — may read available local Memory files without calling Ada's scoped API. The native local-chat path runs under the logged-in user's permissions; running a process in a container does not by itself provide per-person confidentiality. No stronger guarantee may be advertised.

Revisit OS/process isolation if untrusted code execution, different OS-level users, or a stronger threat model becomes a concrete requirement. Do not connect real household data until trusted identity/audience binding and end-to-end scoped access are implemented and verified.

## MVP-30 acceptance gates

- Test two synthetic private users and a shared audience: authorized and forbidden reads, writes, retrieval hits, model-context assembly and responses.
- Trusted identity and intended audience come from the authenticated interaction/channel, not text. Unknown/forged context fails closed.
- Apply the same checks to independently configured source/document providers and derived indexes; do not give the model a generic filesystem escape hatch.
- Preserve Markdown/history/recovery behavior. Explicitly settle ADR-0010's late non-cooperating-save race, Git executable-metadata safety, and operator backup/restore expectations.
- Document and verify the difference between Ada-level authorization and Mac/device security. Independent review and exact-head tests precede MVP completion.

This ADR accepts **scope**, not a production-ready implementation, deployment topology or authentication scheme.
