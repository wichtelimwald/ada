# iCalendar parsing/recurrence dependencies: focused adoption review

- **Date:** 2026-09-27
- **Scope:** MVP-60 slices S1-S3 (CalDAV read path and create). Dependency
  adoption in source and local builds only; not a redistribution clearance.
- **Prior evidence:** [calendar provider evaluation](calendar-provider-evaluation.md)
  section 6 (candidate comparison, R1 recurrence decision) and
  [ADR-0009](../decisions/ADR-0009-calendar-provider-integration.md) section 5,
  both accepted 2026-09-26. This note adds the focused provenance/security/
  installed-artifact check the technology-evaluation skill requires before
  adoption, and records it in NOTICE.md.

## Why these dependencies

OX/IONOS does not expand recurrences server-side (evaluation section 3), and
Ada must not hand-roll RFC 5545 parsing/serialization or RRULE/EXDATE/
RECURRENCE-ID expansion — both are classic sources of silent calendar bugs
(evaluation section 6). Ada adopts:

- **`icalendar` 7.3.0** (BSD-2-Clause) for RFC 5545 parsing/serialization.
- **`recurring-ical-events` 3.8.2** (LGPL-3.0-or-later) for client-side
  recurrence expansion, used unmodified (decision D1).
- **`x-wr-timezone` 2.0.1** (LGPL-3.0-or-later), a direct dependency of
  `recurring-ical-events`, for non-standard `X-WR-TIMEZONE` handling.

## Provenance, maintenance, and security

Checked 2026-09-27.

- **`icalendar`** — maintained by the Plone Foundation / `collective`
  organization on GitHub. Publishes security advisories and offers GitHub's
  private vulnerability reporting route. Two advisories are on record, **both
  fixed below the adopted version**:
  - GHSA-cv84-9p8j-fj68 (High): `Component.__eq__` recursive comparison is
    exponential in nesting depth (~13 minutes CPU from an ~800-byte, 30-level
    payload). Affects 7.1.0-7.1.2; fixed in **7.1.3**.
  - GHSA-qjcq-q7h7-r74v (Moderate): unbounded `VALARM` `REPEAT` expansion
    (3,000,000 repeats measured at 504 MB / 4.35 s). Affects >=6.1.0; fixed in
    **7.2.2**, which caps expansion at `icalendar.config.MAX_ALARM_REPEAT`
    (default 10,000).

  Version 7.3.0 is patched for both. Ada's S2 read path does not call the
  vulnerable alarm-time-expansion API and does not compare parsed components
  for equality; ADR-0009's own deterministic complexity limits (components/
  properties per response, expanded occurrences per series/query) are the
  primary control for untrusted calendar data regardless of upstream caps, and
  must not assume every future upstream release is free of a similar issue.
- **`recurring-ical-events`** — maintained by `niccokunzmann`; no published
  advisories; security contact is Tidelift coordinated disclosure. Release
  3.8.2 is dated 2026-04-30; repository activity observed through 2026-09
  (evaluation section 6).
- **`x-wr-timezone`** — same maintainer; no published advisories; same Tidelift
  contact.

This is a review of currently published advisories, not proof that unknown
vulnerabilities do not exist, matching the standard already applied to
`httpx2` ([review](httpx2-direct-transport-review.md)).

## License and artifact evidence

Installed 2026-09-27 into an Ada-only macOS Python 3.14.6 environment
(`pip install icalendar==7.3.0 recurring-ical-events==3.8.2 x-wr-timezone==2.0.1`
on top of Ada's existing `pyproject.toml` dependencies):

| Package | Version | Declared license | Wheel | Native files |
| --- | --- | --- | --- | --- |
| `icalendar` | 7.3.0 | `License-Expression: BSD-2-Clause` (`LICENSE.rst`, Plone Foundation copyright) | `py3-none-any` | none |
| `recurring-ical-events` | 3.8.2 | `License-Expression: LGPL-3.0-or-later` | `py3-none-any` | none |
| `x-wr-timezone` | 2.0.1 | `License: LGPL-3.0-or-later` | `py3-none-any` | none |

Transitive packages newly resolved or already present:

| Package | Version | Declared license | Pulled in by |
| --- | --- | --- | --- |
| `tzdata` | 2026.4 | Apache-2.0 (`LICENSE`, `licenses/LICENSE_APACHE`) | `icalendar` (`tzdata>=2025.3`) |
| `python-dateutil` | 2.9.0.post0 | "Dual License" (Apache-2.0 / BSD, per package `LICENSE`) | already required (was already installed) |
| `six` | 1.17.0 | MIT | `python-dateutil` (already installed) |
| `click` | 8.5.0 | `License-Expression: BSD-3-Clause` | already required by `dbos`; `x-wr-timezone` also declares it, no new transitive edge |

All four wheels are `py3-none-any` with no `.so`/`.dylib`/`.dll` files in
their `RECORD`, matching the pure-Python profile already established for
`httpx2`/`httpcore2`. `python-dateutil` and `six` were already resolved by the
existing dependency graph; only `tzdata` is a genuinely new transitive
package.

## LGPL obligations

`recurring-ical-events` and `x-wr-timezone` are LGPL-3.0-or-later, used
**unmodified** as separately installed packages (decision D1; not vendored,
not statically linked into a single binary). This is the same obligation
class as the existing `dbos` -> `psycopg` -> `psycopg-binary` LGPL-3.0-only
path already on record in NOTICE.md: source-code use and unmodified dynamic
use do not themselves require Ada's own code to be relicensed, but
**redistributing a built Ada image or installer** that bundles these
packages must satisfy LGPL sections 4/5 (make the LGPL component's source and
version available, permit replacement, do not fully static-link it into a
way that would prevent that) before publication. Ada's current release mode
(project source, dependency manifest, Dockerfile for local builds; no
prebuilt runtime image or installer) does not yet trigger that obligation;
the existing NOTICE.md "release scope" section already gates any future
built-artifact release on a dedicated check, and this entry is added to that
gate rather than duplicating it.

## Compatibility with Ada's MIT code

BSD-2-Clause (`icalendar`), Apache-2.0 (`tzdata`), the dual Apache-2.0/BSD
license (`python-dateutil`), and MIT (`six`) are permissive and compatible
with Ada's MIT-owned source, subject to their own notice/attribution
requirements. LGPL-3.0-or-later (`recurring-ical-events`, `x-wr-timezone`) is
compatible with unmodified separate-package use under the terms above; it is
not merged into Ada's MIT code and Ada's own code is not relicensed.

## Decision

Adopt `icalendar==7.3.0`, `recurring-ical-events==3.8.2`, and
`x-wr-timezone==2.0.1` as pinned direct dependencies, recorded in
`pyproject.toml` and NOTICE.md in the same change that introduces the first
import (S2 CalDAV read path).

**Re-open when:** a new relevant security advisory appears for any of the
three packages, an upgrade is proposed, Ada publishes a prebuilt runtime
image or installer (LGPL sections 4/5 obligations must be satisfied first),
or `recurring-ical-events`/`x-wr-timezone` maintenance materially changes
(evaluation section 6 already treats R2 - Ada-owned expansion on
`python-dateutil` `rrule` - as the fallback if LGPL obligations later prove
unacceptable for a distribution mode).
