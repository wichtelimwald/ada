# IONOS Mail Business CalDAV probe (MVP-60)

**Status:** prepared, not yet executed. The scripts were syntax-checked and the
summarizer was exercised against synthetic XML only; they have **not** been run
against IONOS.

This probe collects the provider facts that
[ADR-0009](../../docs/decisions/ADR-0009-calendar-provider-integration.md) and
the [MVP-60 step plan](../../docs/plans/MVP-60-real-calendar-provider.md) treat
as open. Public Open-Xchange documentation and python-caldav's compatibility
notes (see [the evaluation](../../docs/research/calendar-provider-evaluation.md))
describe OX App Suite in general or a self-hosted OX test image. IONOS may
configure OX differently.

## Rules

- Use **synthetic calendars and events only**. Do not point the probe at a real
  family calendar.
- The output is designed to contain only status codes, structural properties and
  synthetic `Ada probe` / `Probe place` values. Review it before sharing anyway.
- Credentials are read interactively and passed to `curl` through stdin, not
  command-line arguments. Do not paste the app password into chat, an issue, a
  PR or a file.
- Revoke the probe app password afterwards unless it becomes the development
  credential by explicit decision.

## Webmail preparation

| Step | Where | Action |
| --- | --- | --- |
| W1 | IONOS contract | Create a dedicated Ada mailbox (the intended Ada identity). |
| W2 | Ada webmail → My Account → Login & Security | Enable two-step verification. Create an app password named `Ada CalDAV probe`. |
| W3 | Ada webmail → Calendar | Create calendar `Ada probe`. Copy its CalDAV URL (calendar ⋯ → Properties). |
| W4 | Second mailbox in the **same** IONOS contract | Create **new** calendars `Ada probe shared RO` and `Ada probe shared RW`. Share RO with the Ada mailbox as viewer/read-only; share RW with write/author rights. In `shared RO`, on one date, create: `Ada probe public` (location `Probe place A`); `Ada probe confidential` (location `Probe place B`) using the strongest-but-one privacy option; `Ada probe private` (location `Probe place C`) using the strongest privacy option, if the UI offers two levels. |
| W5 | Ada webmail → Calendar → shared calendars | Copy the CalDAV URLs of both shared calendars (Properties). |

Record these manual observations with the probe output:

- **M1:** Does the app-password dialog offer an application type/scope (for example CalDAV only), or only a name?
- **M2:** Which privacy options does the event dialog offer, with their exact UI labels?
- **M3:** Does the properties dialog show a CalDAV URL for calendars shared *with* the Ada mailbox?
- **M4:** After the probe, did the second mailbox receive any notification email about events Ada created in `shared RW`?

## Run

```bash
zsh research/calendar/ionos_caldav_probe.zsh
```

Requirements: macOS zsh, `curl`, `uuidgen`, BSD `date`, Python 3 standard
library (`ADA_PYTHON` may point to a specific interpreter). The probe cleans up
the events it created and prints the cleanup status.

## What each result decides

| Probe | Question | Decision affected |
| --- | --- | --- |
| P1, P6, M3 | Are calendars shared with the Ada mailbox visible via CalDAV, and do read-only shares reject writes? | ADR-0009 access topology (Ada-owned account + provider-side sharing). A failure here re-opens the topology decision. |
| P2 | Does `If-None-Match: *` reject a repeated create, and is a duplicate UID rejected? | Create capability: provider-native create-only (`IDEMPOTENT`) vs reconcile-by-GET (`RECONCILABLE`). |
| P3 | Are UID and resource name preserved; are `X-` properties kept? | Event identity/reconciliation; whether Ada may tag its own events with provenance properties. |
| P4, P7 | Are updates/deletes ETag-conditional; is a blind overwrite rejected? | Update/cancel concurrency and reconciliation design. |
| P5, M2 | What does a viewer see for confidential/private events? | Busy-vs-detail privacy semantics and conflict-check coverage. |
| P8 | Does the server hide events outside a query window? | Supported look-ahead/look-back range and user-visible limits. |
| P9, M1 | Does the app password also grant IMAP? | Credential blast radius (residual risk vs narrower credential). |
| M4 | Does creating an attendee-less event notify anybody? | Whether calendar writes can cause unintended email side effects. |

Record the results (redacted as needed) in the MVP-60 PR and summarize the
durable conclusions in the evaluation document.
