# Threat model — initial skeleton

**Status:** Draft. This is a discovery artifact, not a complete security assessment.

## Assets to protect

- personal memory and conversation history,
- private files and documents,
- credentials and authentication material,
- contacts and communications,
- microphone/camera/screen data,
- browser/session data,
- operating-system integrity,
- user intent and control,
- durable action/workflow state and provider outcome evidence,
- ephemeral local-chat conversation context.

## Initial threat actors

- an author or sender of a website, document, message, email, or other content Ada reads,
- a compromised dependency, plugin, skill, MCP server, model, model artifact, or update source,
- a person with physical or local access to an unlocked device,
- a bystander, household member, visitor, or colleague within microphone/camera range,
- a remote model, cloud, telemetry, sync, or service provider and its compromise/failure modes,
- the legitimate user accidentally authorizing a destructive or privacy-sensitive action.

## Initial trust boundaries

- user ↔ assistant UI,
- assistant/model ↔ persisted memory,
- model ↔ deterministic tool/policy layer,
- policy/tool layer ↔ operating system,
- local components ↔ explicit remote-egress boundary,
- trusted project code ↔ third-party dependencies/plugins/models,
- AdaGuard ↔ pinned `cedarpy` / embedded Cedar native policy engine,
- external content ↔ model context,
- Ada durable-action semantics ↔ DBOS system database / recovery engine,
- DBOS workflow steps ↔ external providers with their own idempotency/reconciliation semantics,
- Ada agent-runtime adapter ↔ separately running loopback Ollama/model process,
- verified actor/audience ↔ AdaGuard authorization ↔ scoped Memory/source access,
- restricted MVP admin chat ↔ trusted administrator authority ↔ grant setup/change/revocation (no model-derived privileges),
- Ada's trusted Memory API ↔ locally accessible files and separately configured source/document providers,
- model/data/quoted input ↔ trusted Memory access APIs (no unrestricted model filesystem tools),
- native macOS local-chat process ↔ host resources accessible to the logged-in
  user; a bridged Dev Container does not isolate this separate native process.

## Ada KDBX credentials — observed same-UID attack (PR #57)

**Status:** Proven for the reviewed Docker Desktop/LinuxKit test environment at
`c3762db30030814e8499d1ffef3ebeab88217421`, with synthetic secrets.
This is **not** a general Linux/kernel or macOS-wide guarantee. The agent
review is not an independent human security audit.

- **Assets:** Ada-only `secrets/ada.kdbx` at rest; master passphrase in the
  unlocked process; **all** plaintext vault entries; encrypted backups
  decryptable with the same master passphrase.
- **Trust boundaries:** trusted Ada code vs. any *other process sharing the
  container's UID and PID namespace*; Python KDBX reader vs. decrypted values
  in process memory; the IDE/server/extensions/terminals/AI agents vs. a
  credential-bearing process; container vs. host/root administrative access.
- **Observed attack:** With the documented Docker `--cap-drop=ALL` and
  `--security-opt=no-new-privileges` settings, a sibling process with UID
  `ada` read the master passphrase and decrypted entry passwords through
  `/proc/<pid>/mem` on the reviewed Docker Desktop LinuxKit kernel without
  Yama LSM. A read-only KDBX mount does **not** prevent disclosure. Network
  access in the VS Code container can compound the consequences.
- **Lifetime risk:** `kdbxtool` retains a normal Python `str` master
  passphrase and key material while open. Its `zeroize_credentials()` only
  zeroes a *copy* of the transformed immutable bytes; decrypted entry
  strings have been observed to persist after `lock()` and garbage collection.
  `lock()` detaches the database and stops authorized lookups, but does
  **not** promise memory erasure. Process exit reduces lifetime, without
  proving that every memory copy is scrubbed.
- **Current accepted scope:** **synthetic secrets only**. The optional VS
  Code KDBX Dev Container is a shared, networked development process space,
  not a production secret runtime. Existing secret-reference allowlists
  constrain calls by trusted code, **not** already-compromised processes.
- **Verified limitation of non-dumpability (PR #59 review B1):** Linux checks
  `/proc/<pid>/mem` and `/proc/<pid>/maps` access when the descriptor is
  **opened**, not at every subsequent read. A same-UID sibling that opens
  the victim's `mem` descriptor during Python startup, **before**
  `PR_SET_DUMPABLE=0`, can keep reading after the flag is set. The reviewer
  reproduced this 5/5 using a real terminal prompt: both a master passphrase
  during unlock and a decrypted entry after unlock were accessible.
  Freshly opened descriptors **after** `prctl` were correctly denied.
  `PR_SET_DUMPABLE=0` is only defense against **late** readers, not a
  standalone same-UID isolation mechanism.
- **Mandatory before any real credentials:** ensure that **from process
  startup** no untrusted same-UID process shares the credential process's
  PID namespace. Use a dedicated single-purpose container/process and a UID
  not shared with IDE extensions, agents, helper processes or workloads;
  forbid `docker exec`/sidecars in that namespace during unlock. Applying
  `PR_SET_DUMPABLE=0` *before the prompt* remains defense in depth and must
  fail closed. The acceptance test must cover both a fresh late-opening
  sibling **and an attacker already running before unlock that pre-opens a
  descriptor during process startup**; the latter must have no access in
  the chosen runtime topology. Optionally add a fail-closed process
  enumeration gate, understanding that a `/proc` snapshot has races and
  is **not** a substitute for isolation. Host/root privilege remains out of
  scope. Release retained password/key references promptly, reject weak
  Argon2 before derivation, review and lock the **entire** dependency
  graph, audit `kdbxtool` and prevent unnecessary network egress.
  Put a Docker `--memory` limit around the credential process to bound
  post-authentication decompression/resource exhaustion. Review backups,
  sync and crash/swap handling before live use.
- **Hardening state (issue #58):** `PR_SET_DUMPABLE=0`, its adapter-side
  check, bounded KDBX4/Argon2 preflight, a single `O_NOFOLLOW` file
  descriptor, and early reader credential-reference release are implemented
  and have synthetic target-side tests. The tests prove **late-opener**
  denial, not the required pre-open race defense. The research-only VS
  Code Dev Container remains unsafe for real credentials. No fully isolated
  credential runtime or production-reader approval exists.
- **Residual even after hardening:** code in the credential-bearing Ada
  process can read every decrypted credential. OS administrators/container
  host privilege, possible compromised dependencies, immutable Python string
  remnants and backups remain outside the app's guarantee. A runtime
  process-hardening flag is not a substitute for a trusted code base.

## Threats to evaluate

- direct and indirect prompt injection,
- malicious or compromised web/file/tool content,
- excessive agent authority,
- memory poisoning,
- accidental destructive actions,
- sensitive-data leakage to cloud/sync/telemetry providers,
- secrets in prompts/logs/memory,
- supply-chain compromise,
- authorization-engine/binding compromise or semantic drift,
- malicious or invalid grant/policy configuration,
- attacker-controlled time/provenance/assurance context attempting to expand authority,
- malicious plugins/skills/MCP servers/model artifacts,
- sandbox escape or local privilege escalation,
- unauthorized microphone/camera/screen capture,
- bystander capture without appropriate product controls,
- insecure remote/mobile control if introduced,
- denial of service / runaway automation,
- misleading or unusable approval prompts,
- duplicate external side effects after crash/recovery,
- durable workflow payloads retaining more personal data than recovery requires,
- workflow-ID collision or replay causing the wrong operation result to be reused,
- provider ambiguity being misreported as success,
- accidental configuration of the "local" model profile to send prompts/history to a non-loopback endpoint,
- a compromised or malicious local model artifact producing manipulative or privilege-seeking output,
- ephemeral conversation context being mistaken for authoritative long-term Memory,
- untrusted content or model output silently rewriting the persistent personality,
- personality drift being used to smuggle new authority, disclosure rules, or false action claims into model behavior.
- native local-chat dependencies or executed code accessing resources available
  to the logged-in macOS user.

## Initial design targets

- local-first processing,
- least privilege,
- deterministic policy enforcement,
- explicit high-impact approvals,
- clear cloud-egress disclosure,
- reversible actions where practical,
- auditable behavior without sensitive logs,
- dependency provenance and pinning strategy,
- fail-closed behavior for sensitive authorization boundaries,
- Ada-owned authorization request/decision types with Cedar isolated behind AdaGuard,
- pinned Cedar binding/engine plus permanent conformance tests on upgrades,
- policy/schema validation before activation,
- trusted Guard-owned clock for expiry evaluation rather than caller/model-provided time,
- privileged grant/policy mutation separate from policy evaluation,
- stable Ada operation IDs reused as durable workflow identities,
- each operation ID bound to canonical immutable action metadata and mismatched replays rejected before returning a durable result,
- provider-native idempotency/reconciliation preferred before retrying consequential writes,
- unreconcilable external outcomes fail to explicit `ambiguous` rather than blind retry,
- DBOS isolated behind an Ada-owned durable-action port,
- minimal durable workflow payloads with no raw prompts/messages/secrets merely for convenience,
- production-provider review of sensitive action-payload storage before real personal data is connected,
- first local-model profile restricted in code to loopback HTTP(S) endpoints,
- local model output remains proposal/data and never becomes authorization,
- local-chat history remains process-local runtime context until deterministic Memory writes and verified actor/audience-scoped access are implemented,
- model/runtime artifact provenance and pinning reviewed before Ada distributes or auto-provisions model artifacts,
- personality bootstrap seed copied only into empty authoritative Memory; existing Memory wins,
- persistent personality changes must be inspectable, reversible, attributable, and isolated from permissions/privacy/action-truth rules,
- untrusted content/model output cannot directly persist personality changes,
- every model-originated Memory write/promotion passes an Ada-owned deterministic validation boundary for source/trust, privacy scope, learning class/sensitivity, provenance/lifecycle, and contradiction/correction semantics,
- require trusted administrator binding for the restricted MVP admin chat before granting/revoking permissions; an arbitrary prompt or ordinary email cannot elevate authority;
- bind reliable actor identity, audience and authorization to Memory reads,
  writes, retrieval/context construction, source-provider access and disclosure;
  ambiguity or absence must fail closed;
- use trusted AdaGuard/application policy, never model text, retrieved content,
  filenames or caller-provided domains, to decide permitted private/shared scopes;
- verify the complete application-level data flow with synthetic positive and
  negative tests. An in-memory scope contract is not end-to-end security;
- never expose unrestricted model filesystem tools or bypass scoped checks
  through derived indexes, source-provider adapters or raw tool results;
- **MVP residual (ADR-0012):** Ada provides no OS-enforced isolation of
  local Memory from other processes of the same logged-in macOS user or
  compromised Ada/runtime dependency code with equivalent filesystem rights.
  Account security, disk encryption, sync and backup are owned by the operator;
  neither a separate broker service nor per-person encryption is promised;
- configure source/document providers independently by logical scope, while
  enforcing the same application-level permissions across those providers;
- for the first live calendar trial, use real registered household accounts with only deliberately non-sensitive test records, and require verified sender, scoped grants, deduplication and recovery before enabling any provider effects; no confidential data during pilot does not replace authorization;
- keep the first macOS chat CLI native alongside a loopback-bound Ollama and
  run development and tests in the default bridged Dev Container; review any
  future container-to-host Ollama connection before enabling it.

Update this document whenever a new trust boundary, threat actor, data flow, or privileged capability is introduced.
