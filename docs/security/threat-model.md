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

## Initial trust boundaries

- user ↔ assistant UI,
- assistant/model ↔ persisted memory,
- model ↔ tool/policy layer,
- tool layer ↔ operating system,
- local components ↔ remote services,
- trusted project code ↔ third-party dependencies/plugins/models,
- external content ↔ model context.

## Threats to evaluate

- direct and indirect prompt injection,
- malicious or compromised web/file/tool content,
- excessive agent authority,
- memory poisoning,
- accidental destructive actions,
- sensitive-data leakage to cloud providers,
- secrets in prompts/logs/memory,
- supply-chain compromise,
- malicious plugins/skills/MCP servers/model artifacts,
- sandbox escape or local privilege escalation,
- unauthorized microphone/camera/screen capture,
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

Update this document whenever a new trust boundary or privileged capability is introduced.
