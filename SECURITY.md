# Security policy

Ada is currently in product discovery and architecture exploration. There is no production release yet.

## Security principles

- Least privilege for filesystem, network, application, credential, camera, microphone, and automation access.
- Deterministic runtime policy enforcement; never rely on prompts alone for security boundaries.
- Treat external content and model output as untrusted input.
- Human approval for destructive, external, financially relevant, or otherwise high-impact actions.
- No hardcoded secrets or credentials.
- No silent installation or execution of third-party plugins, skills, binaries, MCP servers, or hooks.
- Dependencies and model artifacts require provenance and license review.
- Security-sensitive behavior must have runnable verification before merge.

## Reporting vulnerabilities

Please do not publish exploit details in a public issue. Use GitHub private vulnerability reporting once it is enabled for this repository. Until then, contact the repository owner privately through the contact options on the maintainer's GitHub profile.

## Scope

The initial threat model is maintained in `docs/security/threat-model.md` and must evolve with the architecture.
