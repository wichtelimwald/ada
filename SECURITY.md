# Security policy

Ada has an implementation foundation and narrow local-chat/synthetic action slices, but no production release. Current architecture status lives in `docs/decisions/`, open work in `docs/todo.md`, and active implementation/review state in GitHub.

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

Please do not publish vulnerability or exploit details in a public issue.

GitHub Private Vulnerability Reporting is the intended reporting channel and is enabled for this repository. Do not publish sensitive vulnerability details publicly.

## Scope

The initial threat model is maintained in `docs/security/threat-model.md` and must evolve with the architecture.
