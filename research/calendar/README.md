# IONOS Mail Business CalDAV probe (MVP-60)

**Status:** prepared, not yet run against IONOS. The script was syntax-checked
and run end-to-end against a local HTTPS fake CalDAV server that uses synthetic
data. The summarizer was exercised against synthetic XML.

This probe collects the provider facts that
[ADR-0009](../../docs/decisions/ADR-0009-calendar-provider-integration.md) and
the [MVP-60 step plan](../../docs/plans/MVP-60-real-calendar-provider.md) treat
as open. Public Open-Xchange documentation and python-caldav's compatibility
notes (see [the evaluation](../../docs/research/calendar-provider-evaluation.md))
describe OX App Suite in general or a self-hosted OX test image. IONOS may
configure OX differently.

The MVP access model is **Ada-owned calendars**: Ada's own mailbox holds one
calendar per family member plus one family calendar, and shares them outward.
The core probe therefore needs only Ada's mailbox. The inbound-sharing probes
(P5, P6) are optional and need a second mailbox in the same IONOS contract.

## Rules

- Use **synthetic calendars and events only**. Do not point the probe at a
  calendar that holds real appointments.
- The output is designed to contain only status codes, structural properties and
  synthetic `Ada probe` / `Probe place` values. Review it before sharing anyway.
- Enter the app password **only** at the probe's hidden prompt. Never paste it
  into chat, an issue, a PR, a file or a shell command line. A password that was
  pasted anywhere else must be revoked and replaced.
- Share links are bearer secrets: anyone with the link can read the calendar.
  The probe reads the link through a hidden prompt; do not post it.
- Revoke the probe app password afterwards unless it becomes the development
  credential by explicit decision.

## Webmail preparation

| Step | Where | Action |
| --- | --- | --- |
| W1 | IONOS contract | Dedicated Ada mailbox (the intended Ada identity). |
| W2 | Ada webmail → My Account → Login & Security | Enable two-step verification. Create an app password named `Ada CalDAV probe`. |
| W3 | Ada webmail → Calendar | Create calendar `Ada probe`. Copy its CalDAV URL (calendar ⋯ → Properties). |
| W4 | Ada webmail → Calendar → `Ada probe` → share | Share the calendar outward the way family members would receive it: a read-only link and, if offered, an invitation to one of **your own** external addresses. Copy the link for the probe's hidden prompt. Optionally subscribe to it on your own iPhone/Mac. |
| W5 (optional) | Second mailbox in the **same** contract | Only if such a mailbox exists: create synthetic calendars `Ada probe shared RO` / `Ada probe shared RW`, share them with Ada (viewer / author), and add the synthetic events described for P5. Not needed for the MVP model. |

For P5 (optional), the `shared RO` calendar needs, on one date:
`Ada probe public` (location `Probe place A`), `Ada probe confidential`
(location `Probe place B`, strongest-but-one privacy option) and
`Ada probe private` (location `Probe place C`, strongest privacy option).

Record these manual observations with the probe output:

- **M1:** Does the app-password dialog offer an application type/scope (for example CalDAV only), or only a name?
- **M2:** Which outward sharing options does webmail offer for Ada's calendars: invite by external address, anonymous link, read-only vs read/write, expiry, PIN? Does an invited guest see anything besides the shared calendar?
- **M3:** Can the share be subscribed in Apple Calendar (and Google Calendar, if used), and how long does an event created by the probe take to appear there?
- **M4:** Did the invited external address receive any email when the probe created, changed or deleted events?

## Run

```bash
zsh research/calendar/ionos_caldav_probe.zsh
```

Requirements: macOS zsh, `curl`, `uuidgen`, BSD `date`, Python 3 standard
library (`ADA_PYTHON` may point to a specific interpreter). Press Enter to skip
optional inputs. The probe deletes the events it created and prints the cleanup
status.

## What each result decides

| Probe | Question | Decision affected |
| --- | --- | --- |
| P1 | Is Ada's calendar listed with write privileges; are change tokens (`getctag`, `sync-token`) offered? | Basic CalDAV usability; later change detection. |
| P2 | Does `If-None-Match: *` reject a repeated create, and is a duplicate UID rejected? | Create capability: provider-native create-only (`IDEMPOTENT`) vs reconcile-by-GET (`RECONCILABLE`). |
| P3 | Are UID and resource name preserved; are `X-` properties kept? | Event identity/reconciliation; whether Ada may tag its own events with provenance properties. |
| P4, P7 | Are updates/deletes ETag-conditional; is a blind overwrite rejected? | Update/cancel concurrency and reconciliation design. |
| P8 | Does the server hide events outside a query window? | Supported look-ahead/look-back range and user-visible limits. |
| P9, M1 | Does the app password also grant IMAP? | Credential blast radius (residual risk vs narrower credential). |
| P10, M2, M3 | Does the outward share deliver current iCalendar data, and how do family members receive it? | Feasibility and UX of the Ada-owned calendar model (read-only subscriptions, refresh latency). |
| M4 | Do Ada's writes notify guests? | Whether calendar writes can cause unintended email side effects. |
| P5, P6 (optional) | Inbound sharing: visibility of confidential/private events; enforcement of read-only shares. | Only for the later "users share their own calendars with Ada" option. |

Record the results (redacted as needed) in the MVP-60 PR and summarize the
durable conclusions in the evaluation document.
