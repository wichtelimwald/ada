# Skill: Security and privacy design

Use for any feature that reads personal data, changes permissions, invokes tools, persists memory, connects to external services, or can affect the operating system.

## Questions

- What data enters the component?
- Which input is untrusted?
- What authority does the component have?
- Can untrusted content influence a privileged action?
- What data is stored, where, and for how long?
- Can data leave the device? Through which exact path?
- What happens if the model is wrong or maliciously instructed?
- Which actions require user approval?
- What is the rollback/recovery path?
- What logs or diagnostics could leak sensitive information?
- Which third-party code or model artifacts execute locally?

## Required properties

- least privilege,
- explicit trust boundaries,
- fail closed for sensitive permissions,
- deterministic policy enforcement,
- secrets outside normal memory,
- user-visible cloud egress,
- sanitised/redacted logs,
- supply-chain provenance,
- testable security invariants.

Update `docs/security/threat-model.md` when a trust boundary changes.
