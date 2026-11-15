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

## MVP-60 S6 — operator-only CalDAV read probe (not yet live-approved)

The `calendar-probe` command is the first credential-to-provider integration:
an operator manually unlocks Ada's **own KDBX vault**, the CLI retrieves only
the allowlisted app-password entry, checks provider-reported collection
privileges and reads events for the next seven days. It prints **counts only**,
does not write events or persist provider data, and is not available as a
model-facing tool. Do not use private family data in the initial pilot.

Use one **owner-only JSON configuration file outside the source repository**,
with no password, token or vault master passphrase in it. Example values
below are intentionally fake; supply your actual trusted IONOS CalDAV origin,
Ada account, calendar collection path and audience/mode only after review:

```json
{
  "provider": "ionos",
  "base_url": "https://dav.example.invalid",
  "username": "ada@example.invalid",
  "password_ref": "ionos/calendar",
  "calendars": [
    {
      "id": "family-test",
      "collection": "/caldav/example-test/",
      "audience": "family",
      "mode": "write"
    }
  ]
}
```

Save it as a private file and apply `chmod 600 /path/to/ada-caldav-pilot.json`.
The `password_ref` must exactly match the title of an entry in the Ada-only
KDBX file; that entry contains the app password **only inside the vault**.
The provider-reported `read`/`write` privileges must match the configured
`mode`. A mismatch fails closed before calendar events are requested.

The reviewed ID-based launcher remains the only credential-bearing startup
path. After the S6 PR's own review and target checks, the operator can point
`ADA_CALDAV_CONFIG` at this file and invoke
`sh scripts/run_ada_credentials.sh calendar-probe` with the existing
`ADA_MEMORY_ROOT` and `ADA_CREDENTIAL_IMAGE_ID` set. Default networking
is `none` and a real provider connection therefore fails closed.
`ADA_CALDAV_ALLOW_NETWORK=1` deliberately opts this one command into Docker
bridge networking; **Docker bridge is not a destination allowlist**. The
trusted Ada CalDAV client constrains its own HTTPS requests to the configured
origin, but a compromised in-process dependency could make arbitrary
connections. Live app credentials must wait until this egress boundary and
the focused S6/S7 security review have explicit acceptance.

No new installed dependency or provider credential is needed to run the
synthetic regression tests. Operation-record retention, live write authority
and real-provider S7 acceptance remain separate work.
