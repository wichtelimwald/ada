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
- Ada agent-runtime adapter ↔ separately running loopback Ollama/model process.
- opt-in host-network development container ↔ other host network services;
  mounted checkout code and editor actions are an execution boundary.

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
- checkout-controlled setup scripts running automatically inside a host-networked
  development container with access to other host services.

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
- local-chat history remains process-local runtime context until the authoritative Memory design is accepted,
- model/runtime artifact provenance and pinning reviewed before Ada distributes or auto-provisions model artifacts,
- personality bootstrap seed copied only into empty authoritative Memory; existing Memory wins,
- persistent personality changes must be inspectable, reversible, attributable, and isolated from permissions/privacy/action-truth rules,
- untrusted content/model output cannot directly persist personality changes.
- no automatic checkout-controlled setup command in the opt-in host-network
  profile; use it only for reviewed code, without private mounts or secrets,
  and run routine validation in the default development profile. Host services
  are still reachable by code deliberately run in this container.

Update this document whenever a new trust boundary, threat actor, data flow, or privileged capability is introduced.
