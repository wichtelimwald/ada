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
- user intent and control.

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
- external content ↔ model context.

## Threats to evaluate

- direct and indirect prompt injection,
- malicious or compromised web/file/tool content,
- excessive agent authority,
- memory poisoning,
- accidental destructive actions,
- sensitive-data leakage to cloud/sync/telemetry providers,
- secrets in prompts/logs/memory,
- supply-chain compromise,
- malicious plugins/skills/MCP servers/model artifacts,
- sandbox escape or local privilege escalation,
- unauthorized microphone/camera/screen capture,
- bystander capture without appropriate product controls,
- insecure remote/mobile control if introduced,
- denial of service / runaway automation,
- misleading or unusable approval prompts.

## Initial design targets

- local-first processing,
- least privilege,
- deterministic policy enforcement,
- explicit high-impact approvals,
- clear cloud-egress disclosure,
- reversible actions where practical,
- auditable behavior without sensitive logs,
- dependency provenance and pinning strategy,
- fail-closed behavior for sensitive authorization boundaries.

Update this document whenever a new trust boundary, threat actor, data flow, or privileged capability is introduced.
