# Manual repository setup

Items that require GitHub UI/admin configuration and are intentionally not performed by coding agents.

## Repository metadata

- [ ] Set description to: `Ada — a local-first, privacy-first personal AI assistant with voice, user-controlled memory, and permissioned computer control.`
- [ ] Suggested topics: `personal-ai`, `local-first`, `privacy`, `voice-assistant`, `ai-agent`, `open-source`.

## Protect `main`

Create a branch ruleset in **Settings → Rules → Rulesets**.

Suggested initial configuration for a solo maintainer:

- [ ] Name: `protect-main`
- [ ] Enforcement: Active
- [ ] Target: default branch / `main`
- [ ] Restrict deletions
- [ ] Block force pushes
- [ ] Require a pull request before merging
- [ ] Required approvals: **0 initially** — this still blocks direct updates while avoiding a self-review deadlock for a solo maintainer
- [ ] Require resolution of pull-request conversations
- [ ] Do **not** require status checks while the project intentionally has no hosted CI
- [ ] Do **not** require Code Owner approval while there is only one maintainer; GitHub does not allow authors to approve their own PRs

If another trusted maintainer joins, reconsider requiring one approval and Code Owner review.

## Merge settings

- [ ] Prefer squash merge for focused history.
- [ ] Consider disabling merge commits if linear history is desired.
- [ ] Enable automatic deletion of merged head branches if preferred.

## Security settings

Under **Settings → Security** / **Code security and analysis**, review and enable where available:

- [ ] Private vulnerability reporting
- [ ] Secret scanning
- [ ] Push protection for secrets
- [ ] Dependabot alerts (runtime update configuration can wait until a package ecosystem exists)

Do not enable workflows merely to satisfy a security checkbox; this repository intentionally starts without GitHub Actions.
