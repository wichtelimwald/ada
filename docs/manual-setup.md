# Manual repository setup

Items that require GitHub UI/admin configuration and are intentionally not performed by coding agents.

**Last verified through the GitHub API:** 2026-09-18.

## Repository metadata

- [x] Repository is public.
- [x] Description: `Ada — a local-first, privacy-first personal AI assistant with voice, user-controlled memory, and permissioned computer control.`
- [x] Topics: `personal-ai`, `local-first`, `privacy`, `voice-assistant`, `ai-agent`, `open-source`.
- [ ] Decide whether the currently enabled GitHub Wiki is wanted; disable it if not.

## Protect `main`

Ruleset `protect-main` is active and currently verifies:

- [x] Target includes the default branch / `main`.
- [x] Restrict deletion.
- [x] Block non-fast-forward updates / force pushes.
- [x] Require a pull request before merging.
- [x] Required approvals: 0 for the solo-maintainer phase.
- [x] Require resolution of pull-request review threads.
- [x] Code Owner approval is not required while there is only one maintainer.
- [x] No required status checks are configured.

### Bypass review

- [ ] Review the ruleset bypass list. The current repository-role entry allows the current maintainer/admin role to bypass the ruleset **always**. Decide whether this emergency escape hatch is intentional or should be removed/restricted.

If another trusted maintainer joins, reconsider one required approval, Code Owner review, stale-review dismissal, and last-push approval.

## Merge settings

- [x] Squash merge enabled.
- [x] Merge commits disabled.
- [x] Automatic deletion of merged head branches enabled.
- [ ] Rebase merge is currently also enabled; keep or disable according to desired history policy.

## Security settings — verify manually

These settings are not reliably exposed through the connected repository API used for this setup:

- [ ] **Private Vulnerability Reporting** — highest priority; `SECURITY.md` assumes this becomes the private reporting channel before a runnable public release.
- [ ] Secret scanning.
- [ ] Push protection for secrets.
- [ ] Dependabot alerts.

Current GitHub navigation for a public repository: **Settings → Security and quality → Advanced Security**. Private Vulnerability Reporting is configured there. Secret scanning for public repositories runs automatically; additional Secret Protection and Push Protection controls are also exposed there where available.

Do not enable GitHub Actions merely to satisfy a security checkbox; Ada intentionally starts without hosted workflows.
