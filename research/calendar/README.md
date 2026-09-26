# IONOS Mail Business CalDAV probe (MVP-60)

**Status:** four maintainer runs against IONOS on 2026-09-26 answered the
questions that shape [ADR-0009](../../docs/decisions/ADR-0009-calendar-provider-integration.md);
results are in the
[evaluation](../../docs/research/calendar-provider-evaluation.md#10-ionos-probe-results).
The probe remains as a **regression check** of Ada's CalDAV assumptions (for
example after IONOS changes). Script changes are smoke-tested end-to-end
against a local HTTPS fake CalDAV server with synthetic data before use.

The probe needs only Ada's mailbox and one synthetic probe calendar. Probes for
inbound sharing, invited guests and anonymous links were used in runs 1–4 and
then removed: IONOS shares calendars only with mailboxes in the same contract,
and anonymous links lead to the web UI (see the evaluation).

## Rules

- Use a **synthetic probe calendar only**. Never point the probe at a calendar
  that holds real appointments.
- The output contains status codes, structural calendar properties, sequence
  numbers, timestamps and counts of synthetic probe events. It never prints
  credentials, calendar names or other event content. Review it before sharing
  anyway.
- The app password is read from the macOS Keychain. Never paste it into chat,
  an issue, a PR, a file or a command line. A password pasted anywhere else must
  be revoked and replaced.

## One-time setup

1. In Ada's webmail, create the calendar `Ada probe` and copy its CalDAV URL
   (calendar ⋯ → Properties; it has the form
   `https://dav.mailbusiness.ionos.de/caldav/<id>`, not the webmail address).
2. Store the non-secret settings in a local file **outside the repository**
   (replace the placeholders):

   ```bash
   mkdir -p ~/.config/ada && printf 'ADA_CALDAV_USER=%s\nADA_CALDAV_PROBE_URL=%s\n' '<ada-mailbox-address>' '<caldav-url>' > ~/.config/ada/caldav-probe.conf
   ```

3. Store the app password in the login Keychain. With `-w` last, `security`
   prompts for it instead of taking it from the command line:

   ```bash
   security add-generic-password -s ada-caldav -a '<ada-mailbox-address>' -w
   ```

   The same Keychain service name is intended for the development adapter
   (plan decision D2). If the item is missing, the probe asks once with hidden
   input.

## Run

```bash
zsh research/calendar/ionos_caldav_probe.zsh
```

Requirements: macOS zsh, `curl`, `uuidgen`, BSD `date`, `security`, Python 3
standard library (`ADA_PYTHON` may point to a specific interpreter). Optional
environment variables: `ADA_PROBE_CONFIG` (other config file),
`ADA_PROBE_IMAP_HOST` (default `imap.ionos.de`). The probe stops before any
write if the calendar listing fails, deletes the events it created and prints
the cleanup status.

## What each result checks

| Probe | Question | Decision affected |
| --- | --- | --- |
| P1 | Is the probe calendar listed with write privileges; are change tokens (`getctag`, `sync-token`) offered? | Basic CalDAV usability; later change detection. |
| P2 | Does `If-None-Match: *` reject a repeated create, and is a duplicate UID rejected? | Create capability (`IDEMPOTENT` via create-only `PUT`). |
| P3 | Are UID and resource name preserved; are `X-` properties kept? | Event identity/reconciliation; provenance marker. |
| P4 | Blind overwrite, stale `If-Match`, conditional updates without `SEQUENCE` changes (P4a–c), and diagnostics on a fresh event (P4d–o: ETag shape, `GET` vs `REPORT` ETag, duplicates). | Update concurrency; ETag normalization. |
| P11 | Which iCalendar fields make an update acceptable? See below. | How Ada writes updates. |
| P7 | Are deletes ETag-conditional; is a repeated delete reported as absent? | Cancel semantics. |
| P8 | Which time ranges do queries cover? | Supported look-ahead/look-back range. |
| P9 | Does the app password also grant IMAP? | Credential blast radius. |

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
| `proper-no-if-match` | fresh blind overwrites are allowed | `If-Match` is required for fresh writes |

Record new results (redacted as needed) in the relevant PR and summarize
durable conclusions in the evaluation document.
