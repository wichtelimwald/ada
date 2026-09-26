# IONOS Mail Business CalDAV probe (MVP-60)

**Status:** runs 1 and 2 against IONOS on 2026-09-26 (results in the
[evaluation](../../docs/research/calendar-provider-evaluation.md#10-ionos-probe-results));
run 3 pending. Script changes are smoke-tested end-to-end against a local HTTPS
fake CalDAV server with synthetic data before each run.

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
- **M3:** Create one event `Ada probe manual` in the probe calendar via webmail. Subscribe to the share link in Apple Calendar (File → New Calendar Subscription; try the link as given and with `?ical=true`). Does the event appear? After changing its time in webmail, how long until the subscription shows it? Delete the event and the subscription afterwards.
- **M4:** Did the invited external address receive any email when the probe created, changed or deleted events?
- **M5:** After the run, is the `Ada probe` calendar in webmail empty? Report any remaining `Ada probe …` event (title only) and delete it manually.

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
| P4, P7 | Are updates/deletes ETag-conditional; is a blind overwrite rejected? P4d–P4o diagnose conditional updates on a fresh event (ETag shape, GET vs REPORT ETag, update before/after a blind overwrite, duplicates). | Update/cancel concurrency and reconciliation design. |
| P8 | Does the server hide events outside a query window? The boundary checks test +11/+13 months and −20/−40 days. | Supported look-ahead/look-back range and user-visible limits. |
| P9, M1 | Does the app password also grant IMAP? | Credential blast radius (residual risk vs narrower credential). |
| P10, M2, M3 | Does the outward share deliver current iCalendar data, and how do family members receive it? | Feasibility and UX of the Ada-owned calendar model (read-only subscriptions, refresh latency). |
| M4 | Do Ada's writes notify guests? | Whether calendar writes can cause unintended email side effects. |
| P11 | Which iCalendar fields make an update "fresh" for IONOS? See the interpretation below. | How Ada writes updates (SEQUENCE/DTSTAMP handling). |
| M5 | Did the probe leave events behind? | Whether a blind overwrite created hidden copies (P4 anomaly). |
| P5, P6 (optional) | Inbound sharing: visibility of confidential/private events; enforcement of read-only shares. | Only for the later "users share their own calendars with Ada" option. |

### Interpreting P11

Each P11 line shows the HTTP status, whether the write was applied, and the
stored `SEQUENCE` before → after. `proper` means fresh `DTSTAMP`, `SEQUENCE`+1
and the current ETag.

| Case | Accepted means | Rejected means |
| --- | --- | --- |
| `old-dtstamp-seq-plus1` | a higher `SEQUENCE` suffices | `DTSTAMP` must be fresh |
| `fresh-dtstamp-seq-equal` | a fresh `DTSTAMP` suffices with equal `SEQUENCE` | `SEQUENCE` must increase |
| `fresh-dtstamp-no-seq` | a fresh `DTSTAMP` suffices even with a lower `SEQUENCE` | `SEQUENCE` is checked |
| `proper-1`, `proper-2` | the standard client path works repeatedly | blocking problem: re-open the update design |
| `proper-wrong-etag` | `If-Match` is not enforced (unexpected) | `If-Match` is enforced (expected) |
| `proper-no-if-match` | fresh blind overwrites are allowed (consistent with P4a) | `If-Match` is required for fresh writes |

`P11-clock-skew` should be a few seconds at most; a larger skew makes the
`DTSTAMP` cases unreliable.

Record the results (redacted as needed) in the MVP-60 PR and summarize the
durable conclusions in the evaluation document.
