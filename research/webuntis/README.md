# WebUntis integration research

> **Status:** research evidence, not an accepted Ada architecture decision
> **Researched:** 2026-09-23
> **Scope:** ways Ada could read school planning and information data from WebUntis without committing the product runtime to one Untis interface

## Executive summary

WebUntis currently exposes several materially different integration surfaces:

1. **Untis Platform APIs** are the documented strategic integration path. They provide modern REST APIs, OAuth/OIDC, server-to-server credentials, tenant isolation, and APIs for timetable data, absences, exams, lessons, rooms, subjects, people, messaging and other school data. The important constraint for Ada is organizational rather than technical: a Platform Application must be registered with Untis and activated for a school. This is not equivalent to a parent creating a personal OAuth client.
2. **Private iCal timetable subscriptions** are the smallest supported solution when Ada only needs timetable data. They avoid password handling and custom API code, but expose only calendar/timetable information and depend on the school's WebUntis configuration.
3. **The legacy WebUntis JSON-RPC API** still works according to current Untis support documentation and has mature open-source clients. It is the most practical route for a personal, read-only prototype when iCal is insufficient. However, Untis has already restricted it for accounts with 2FA enabled, and maintainers of a major community client report an expected future sunset. No official shutdown date was found.
4. **Undocumented browser REST endpoints** expose richer data used by the WebUntis web application and several open-source clients. They can provide details absent from JSON-RPC, but they are not a stable public contract and may change without notice. Ada should treat them as research-only fallback evidence, not as a preferred integration surface.

For Ada, the main architectural conclusion is therefore **not** to make WebUntis itself a domain boundary. The first implementation should remain read-only, capability-driven and replaceable. Before adding any dependency, a real authorized account should be tested locally to establish what the specific school and account type expose.

### Current recommendation

For the first Ada prototype:

1. Check whether the account exposes a private **iCal timetable URL** and whether that already satisfies the initial use case.
2. If richer timetable/change data are required, evaluate **python-webuntis** locally as a replaceable JSON-RPC research adapter. It fits Ada's Python-first direction, is actively maintained as of July 2026, has one runtime dependency, and uses a permissive BSD-3-Clause license.
3. In parallel, ask Untis whether a public, self-hosted, non-commercial open-source project such as Ada can obtain a **Platform Application**, and what school-side activation and contractual requirements would apply.
4. Use undocumented browser REST endpoints only if a concrete required capability is unavailable through supported routes and the stability/security trade-off is explicitly accepted.

No WebUntis runtime dependency is accepted by this research. An ADR is required before a non-trivial provider choice becomes product architecture.

---

## 1. Ada requirements and hard gates

The following requirements follow from Ada's existing trust and engineering model and are relevant before selecting any WebUntis integration mechanism.

### Functional baseline

The initial school-information use case is read-oriented. Likely capabilities include:

- current and future timetable;
- cancellations, substitutions, room/time changes;
- exams;
- homework, if exposed to the authorized account;
- absences, if exposed and actually needed;
- school announcements/messages, if exposed and actually needed.

The exact product scope is still a product decision. Research should not silently turn every technically available field into an Ada feature.

### Security and privacy gates

- Start **read-only**. Do not add write actions merely because an API supports them.
- Treat passwords, TOTP/QR secrets, OAuth client secrets, JWTs, session cookies and private iCal URLs as credentials.
- Never commit, log or place real school credentials, child identifiers or returned school data in fixtures/issues/research artifacts.
- Do not bypass WebUntis account security controls such as 2FA restrictions.
- Minimize local retention of child-related educational data.
- Prefer supported feeds/APIs over browser automation or scraping.
- Keep provider-specific credentials and protocol details behind an Ada-owned boundary.
- Design for revocation and provider migration; school systems and permissions can change independently of Ada.

### Dependency/license gate

Every serious reusable client must have a clear license and distribution story compatible with Ada. A package manifest claiming a license is weaker evidence than an actual repository license file when redistribution is considered.

---

## 2. Integration surface comparison

| Surface | Authentication | Useful data | Stability / support | School or vendor dependency | Ada fit |
| --- | --- | --- | --- | --- | --- |
| **Untis Platform APIs** | OAuth/OIDC user context or OAuth2 client credentials | Broad documented API set incl. timetable, exams, absences, lessons, master data; messaging send | Documented strategic platform | Platform App registration + school activation | Best long-term contract, but not frictionless for a personal MVP |
| **Private iCal subscription** | Secret per-user URL | Timetable/calendar events | Officially supported | Student/guardian availability depends on school module/config | Best KISS path if timetable is sufficient |
| **Legacy JSON-RPC** | WebUntis account/session; community clients also support QR/TOTP patterns | Timetable and master data; client-dependent extras | Still officially functional, but legacy and already restricted with 2FA | Works only where account/API access is enabled | Practical temporary prototype behind replaceable adapter |
| **Undocumented browser REST** | Browser-style session + internal JWT/session mechanisms | Rich timetable details, lesson content, messages and other web-app data | No public compatibility contract | Depends on private implementation details | Research/reference only unless a concrete gap justifies risk |
| **Browser UI automation** | Interactive web login | Whatever UI exposes | Most brittle and operationally expensive | Full dependence on UI behavior | Last resort; not justified while supported interfaces exist |

---

## 3. Official Untis Platform APIs

### 3.1 What they are

Untis documents a modern developer platform at [developer.untis.com](https://developer.untis.com/). The WebUntis API overview currently lists API families including:

- timetable data;
- absences / class register;
- exams;
- lessons;
- rooms;
- subjects;
- students, teachers and classes;
- legal guardians / user management;
- messaging;
- timetable event push.

The API entry point for production is documented as:

```text
https://api.webuntis.com/
```

Untis currently documents a maximum of 40 requests per second and recommends moving larger synchronizations away from peak times.

### 3.2 Authentication model

The platform supports two materially different OAuth flows:

- **OIDC Authorization Code + PKCE** for user-context access;
- **OAuth2 Client Credentials** for server-to-server access.

For server-to-server integrations, credentials are issued per tenant/school. Access tokens are deliberately short-lived; current documentation describes approximately three-minute token validity.

Authorization is separate from authentication. Effective access is limited by both the Platform Application configuration and, for user-context flows, the authenticated user's role and school membership.

### 3.3 Platform Application registration is a real gate

A developer cannot simply create a personal client ID in the way common consumer OAuth systems allow.

Untis describes a process for becoming an integration partner and receiving a Platform Application. The process includes discussing the use case with Untis, receiving an integration environment, validation, and promotion to production.

The registration documentation asks for information such as:

- product and company name;
- use cases;
- APIs/data required;
- a publicly accessible domain;
- integration target group and expected school reach.

The documentation explicitly states that localhost is not supported as the application domain.

Schools then activate the application according to its activation model. For normal opt-in integrations, the school explicitly activates the app and accepts the data exchange. Tenant-specific credentials can be delivered through the documented credential mechanism.

**Ada implication:** the Platform API is technically attractive, but feasibility for a public, self-hosted, non-commercial personal assistant is currently **unverified**. Untis should be asked directly whether that project model is accepted and which contracts/data-processing agreements would apply.

### 3.4 Timetable API is strong

The current timetable documentation recommends the v3 timetable API. It supports:

- real-time timetable periods;
- substitutions;
- cancellations;
- room changes;
- resource/date filtering;
- incremental retrieval based on modification time;
- retrieval of deleted periods.

This is significantly better for robust synchronization than periodically replacing an entire calendar snapshot.

### 3.5 Important current gaps for Ada

Two gaps are relevant to the family-assistant use case:

- The documented Messaging API currently supports **sending**, but the developer documentation states that retrieving the WebUntis message inbox is not supported.
- No documented Platform API for **homework** was found in the current API reference during this research. Homework may exist in other product surfaces, but it should not be assumed to be available through the public Platform API without confirmation.

These are precisely the kinds of gaps that make community clients use additional legacy or internal endpoints.

### 3.6 Privacy / contractual implications

Untis' privacy information for integrations describes third-party integrations as a data exchange initiated by school activation and discusses the integration partner's processor role / contractual relationship.

Ada should therefore separate two questions:

1. **Can the API technically provide the data?**
2. **Can Ada's intended self-hosted/open-source distribution model legally and operationally use that API?**

The second question remains open.

### Assessment

**Strategic candidate, not immediate MVP default.**

It is the strongest documented contract, but organizational onboarding and school activation make it unsuitable to assume as the only path for a family-controlled first prototype.

---

## 4. Private iCal timetable subscription

WebUntis officially supports private dynamic iCal subscriptions.

For an authorized account, the user can obtain a private calendar URL and subscribe to it from an external calendar client. Untis documents the default data window as approximately:

- one week in the past;
- twelve weeks in the future.

The external calendar periodically re-fetches the URL, so changes appear without Ada having to understand WebUntis authentication/session internals.

### Availability

Untis documents different availability by account type/configuration:

- teachers: generally available;
- students and legal guardians: dependent on the relevant school/module configuration.

Therefore availability must be checked with the actual account.

### Security property

The private iCal URL should be treated as a **bearer credential**. Anyone possessing it may be able to read the exposed timetable. It must be stored and redacted like an API token.

### Advantages

- official and simple;
- no account password in Ada;
- no Untis-specific runtime client required;
- naturally read-only;
- the account UI provides a way to disable the subscription link;
- low maintenance burden.

### Limitations

- timetable/calendar only;
- no guaranteed homework, absences, inbox/messages or richer lesson metadata;
- update latency depends partly on the polling behavior of the consumer;
- not suitable if Ada must react to non-calendar school information.

### Assessment

**Preferred first check.**

If the MVP requirement is essentially "know today's/this week's school schedule and changes", this is the KISS option and may avoid an API dependency entirely.

> Note: this personal iCal subscription is distinct from Untis' developer-platform calendar APIs. The developer-side legacy Calendar API is being replaced by the timetable event push mechanism and should not be confused with the user-owned iCal feed.

---

## 5. Legacy WebUntis JSON-RPC API

The well-known endpoint is:

```text
/WebUntis/jsonrpc.do
```

### 5.1 Current official status

Current Untis support documentation still states that the WebUntis JSON-RPC interface continues to function. Untis describes it as an interface historically made available on request for school projects, student developments and smaller in-house projects.

That is stronger evidence than treating it as purely reverse-engineered.

### 5.2 But it is clearly legacy

Untis' 2025 release notes document an important security change: the old JSON-RPC API can no longer be called with a user account that has 2FA enabled.

For Ada this matters because:

- long-term product architecture should not depend on users weakening account security;
- an integration must fail safely when 2FA/API policy changes;
- a prototype should record the actual account's authentication mode rather than assuming username/password will continue to work.

### 5.3 Possible future shutdown

An April 2026 issue in the community project `SchoolUtils/WebUntis` reports, based on conversations with Untis, that the JSON-RPC endpoint is expected to be replaced. The issue author personally estimates a possible 2027 timeframe.

This is **not an official Untis announcement** and the author explicitly states they are not affiliated with Untis. The date must therefore not be treated as a committed sunset date.

Nevertheless, the report aligns directionally with the existence of the new Platform APIs and is a legitimate migration-risk signal.

### 5.4 Ada consequences

JSON-RPC can be reasonable for a **replaceable personal prototype**, but it should not define Ada's school-information domain model.

If used:

- keep the adapter small;
- do not expose JSON-RPC response shapes outside the adapter;
- make capability absence explicit;
- treat authentication failure/security policy change as a normal provider-unavailable state;
- retain a migration path to iCal, Platform APIs or another school provider.

### Assessment

**Pragmatic temporary prototype route; medium-to-high strategic migration risk.**

---

## 6. Undocumented WebUntis browser REST endpoints

The WebUntis web application uses internal HTTP endpoints that community projects have reverse-engineered.

Examples documented by `Naumsede/webuntis-home-assistant` include:

```text
POST /WebUntis/j_spring_security_check
GET  /WebUntis/api/token/new
GET  /WebUntis/api/rest/view/v1/app/data
GET  /WebUntis/api/rest/view/v1/timetable/entries
GET  /WebUntis/api/rest/view/v2/calendar-entry/detail
```

That project documents a browser-style flow involving a `JSESSIONID`, an internal JWT and a tenant ID.

Community implementations use these internal endpoints for data that may be richer than the legacy JSON-RPC surface, such as:

- old/new teacher details on substitutions;
- substitution text;
- lesson content;
- detailed room changes;
- some school messages/announcements.

`UntisPlus` also currently uses a mixture of JSON-RPC and `/api/rest/view/...` endpoints.

### Why this is not the preferred Ada route

These endpoints are implementation details of the WebUntis web client, not a documented public integration contract.

Consequences:

- schemas and paths may change without notice;
- authentication/session behavior may change;
- Untis does not promise compatibility for third-party clients;
- operational incidents may look like Ada defects even when the provider changed;
- reverse-engineered behavior needs stronger regression tests and maintenance.

### Assessment

**Useful research/reference material; production fallback only after a concrete supported-API gap is demonstrated and accepted.**

Browser scraping/automation should rank even lower because it adds UI fragility on top of the same authentication dependency.

---

## 7. Open-source client and reference-project survey

### 7.1 Comparison

| Project | Language | Interface | License evidence | Maintenance signal at research date | Ada role |
| --- | --- | --- | --- | --- | --- |
| [python-webuntis/python-webuntis](https://github.com/python-webuntis/python-webuntis) | Python | JSON-RPC | BSD-3-Clause LICENSE | v0.1.25 / commits July 2026 | **Best current JSON-RPC prototype candidate** |
| [SchoolUtils/WebUntis](https://github.com/SchoolUtils/WebUntis) | TypeScript | JSON-RPC; QR/TOTP auth helpers | MIT LICENSE | Last push April 2024; maintainer says they no longer have own Untis access | Authentication/reference implementation |
| [JonasJoKuJonas/homeassistant-WebUntis](https://github.com/JonasJoKuJonas/homeassistant-WebUntis) | Python | python-webuntis + HA integration | MIT LICENSE | Active through Sept 2026 | Strong operational reference; not a general-purpose library |
| [4biddencode/UntAPI](https://github.com/4biddencode/UntAPI) | TypeScript | JSON-RPC + REST | `package.json` says MIT, **no LICENSE file found** | Created June 2026; essentially initial commit | Capability research only; license gate unresolved |
| [Naumsede/webuntis-home-assistant](https://github.com/Naumsede/webuntis-home-assistant) | Python | Undocumented browser REST | MIT LICENSE | Small, recent 2026 project | Reverse-engineering reference only |
| [ninocss/UntisPlus](https://github.com/ninocss/UntisPlus) | Dart/Flutter | JSON-RPC + internal REST | MIT LICENSE | Very active Sept 2026 | Rich behavior/reference client; poor runtime reuse fit for Python Ada |

### 7.2 python-webuntis

Relevant properties:

- Python, matching Ada's current Python-first direction;
- version 0.1.25 in the repository at research time;
- repository activity in July 2026;
- README states that the project is maintained again;
- only declared runtime dependency is `requests`;
- BSD-3-Clause license in the repository `LICENSE` file.

The project exposes WebUntis session/login and typed convenience objects around the JSON-RPC interface.

#### Strengths for Ada

- smallest language/runtime mismatch;
- permissive license;
- low dependency surface;
- mature project history;
- active enough to justify a prototype.

#### Risks

- inherits all JSON-RPC lifecycle/authentication risks;
- its own API cannot make unavailable WebUntis data appear;
- using it in product code would still require an Ada-owned adapter and explicit failure semantics.

**Research position:** the most credible candidate if a JSON-RPC proof-of-concept is required.

### 7.3 SchoolUtils/WebUntis

Relevant properties:

- TypeScript/Node;
- MIT license;
- supports username/password, anonymous login where enabled, TOTP secret login and WebUntis QR-code credentials;
- package dependencies include Axios and date-fns, with otplib optional;
- repository has not been pushed since April 2024;
- README says the maintainer no longer has direct Untis access for testing.

Its QR/TOTP support is valuable evidence for how WebUntis "Data access" credentials are consumed. The Home Assistant project also points users with iServ/Office365 login to this WebUntis data-access/QR path.

**Research position:** useful authentication/reference implementation, but not a good new runtime dependency for Python-first Ada.

### 7.4 homeassistant-WebUntis

This is an active Home Assistant integration rather than a reusable generic client.

Relevant properties:

- Python;
- MIT;
- active through September 2026;
- currently pins `webuntis==0.1.24` and `PyOTP==2.10.0`;
- supports username/password and QR-code login;
- exposes timetable calendars, next lesson/school start/end, lesson-change events, homework and exam-related entities.

A particularly relevant operational observation in its documentation is:

> exam and homework entities are not available with a parent account; use a student account.

This should be treated as **community implementation evidence**, not a universal Untis guarantee. School modules and permissions vary, so Ada must test the actual authorized account rather than hard-code this assumption.

**Research position:** excellent reference for operational edge cases, polling, account setup and feature availability. Reuse `python-webuntis` directly rather than embedding Home Assistant-specific code unless a specific piece proves independently reusable.

### 7.5 UntAPI

UntAPI is interesting because its README describes a broad WebUntis client with zero runtime dependencies and modules for timetable, exams, homework, absences, substitutions, messages and other data.

However:

- repository created June 2026;
- only minimal project history was found;
- very low adoption signal at research time;
- no repository `LICENSE` file was found;
- `package.json` declares `"license": "MIT"`, but that is insufficient to close Ada's repository-level distribution/license gate.

**Research position:** do not adopt until license provenance and project maturity materially improve. It is useful as a map of possible endpoints/capabilities.

### 7.6 Naumsede/webuntis-home-assistant

This small Python project explicitly states that it uses WebUntis' **undocumented internal browser REST API**.

Its main value is transparent documentation of:

- the session/JWT authentication sequence;
- timetable entry endpoints;
- lesson-detail retrieval;
- richer change information;
- school-message extraction.

It carries an MIT license, but the external WebUntis endpoint contract remains undocumented regardless of the client code license.

**Research position:** reverse-engineering reference, not primary dependency.

### 7.7 UntisPlus

UntisPlus is an actively developed MIT-licensed Flutter client. It demonstrates a broad local-first feature set and currently uses both legacy JSON-RPC and internal REST endpoints.

The codebase is valuable for observing:

- multi-account behavior;
- timetable-change detection;
- homework/exams/absence handling;
- offline caching;
- background synchronization.

Its Dart/Flutter architecture is not a natural dependency for Python-first Ada, and copying its internal-endpoint assumptions would inherit the same compatibility risk.

**Research position:** reference system, not runtime dependency.

---

## 8. Proposed Ada boundary — research hypothesis, not architecture decision

The safest conclusion from the interface diversity is that Ada should own the semantics of school information and keep provider protocols replaceable.

For the **smallest timetable-focused MVP**, a narrow interface is preferable to prematurely defining every possible school feature:

```text
SchoolScheduleSource
    capabilities()
    get_schedule(start, end)
    get_changes(since)   # optional capability
```

Only if product discovery confirms additional needs should the boundary expand toward concepts such as exams, homework, absences or messages.

A future broader shape could conceptually become:

```text
SchoolInformationProvider
    capabilities()
    get_timetable(start, end)
    get_changes(since)
    get_exams(start, end)       # optional
    get_homework(...)           # optional
    get_absences(...)           # optional
    get_messages(...)           # optional
```

This is intentionally **not** an accepted API design. It records the design pressure observed in the research: different WebUntis surfaces expose different subsets, so explicit capabilities are safer than pretending every provider implements one complete schema.

### Provider-specific implementation candidates

```text
Ada-owned school boundary
        |
        +-- iCal adapter
        |
        +-- WebUntis JSON-RPC adapter
        |      +-- python-webuntis candidate
        |
        +-- Untis Platform adapter (future, if onboarding is viable)
        |
        +-- internal WebUntis adapter (fallback only, if explicitly justified)
```

The provider choice must not leak authentication mechanisms or Untis response DTOs into Ada's domain.

---

## 9. Minimal validation plan

### Stage 0 — account capability check, no code

Using the real authorized WebUntis account, inspect:

1. Is a private **iCal** link available?
2. Is **Data access** / a QR code for Untis Mobile available?
3. Is 2FA enabled?
4. Which child/student identities are visible?
5. Which WebUntis UI capabilities are visible to the parent account:
   - timetable;
   - substitutions/changes;
   - exams;
   - homework;
   - absences;
   - messages/announcements?

Do not capture secrets or personal data in GitHub.

### Stage 1 — iCal proof

If iCal is available:

- fetch it locally with its URL supplied only through a secret/environment variable;
- parse a representative period;
- verify cancellations/time/room changes observable through the feed;
- verify update behavior;
- check whether the information satisfies the first product slice.

If yes, stop. Do not add JSON-RPC merely because it is technically available.

### Stage 2 — JSON-RPC proof only if needed

If iCal lacks required data:

- test `python-webuntis` in an isolated research environment;
- use only an authorized test account;
- keep credentials out of commands that may be persisted in shell history where practical;
- retrieve the smallest representative date range;
- characterize exactly what the parent account exposes;
- record behavior, errors and API gaps without recording personal returned data;
- do not yet add it to Ada's runtime dependency set.

### Stage 3 — internal REST only for a demonstrated gap

Only if a product requirement remains unmet:

- identify the exact missing capability;
- verify that the WebUntis web client itself exposes it to the same account;
- test the minimum required internal endpoint read-only;
- document schema/compatibility assumptions and failure behavior;
- explicitly accept the maintenance risk before production use.

### Parallel vendor check

Contact Untis and ask:

- Can an open-source, self-hosted, non-commercial assistant obtain a Platform Application?
- Is a legal entity/company required?
- Can local/self-hosted instances use OIDC/client-credential flows despite the public-domain requirement?
- What activation model would apply for individual schools?
- What DPA/processor obligations apply?
- Is read access to homework or message inbox planned in the Platform APIs?
- Is there an official JSON-RPC retirement plan/date that can be shared?

Those answers could materially change the preferred long-term route and should trigger an update of this research.

---

## 10. Decision/reopen triggers

Revisit the integration decision if any of the following occurs:

- Untis confirms Platform Application eligibility for Ada;
- the school enables/withdraws a required WebUntis module;
- iCal proves sufficient or insufficient for the agreed MVP;
- JSON-RPC authentication stops working or Untis publishes an official deprecation date;
- a supported Platform API adds homework or message-inbox retrieval;
- a serious maintained Python client for the modern Platform API appears;
- a candidate's license or distribution terms change;
- the product scope adds write operations.

A write-capable school integration should be treated as a separate security/authority decision, not as an incremental extension of the read-only prototype.

---

## 11. Known unknowns

This research does **not** establish:

- that Ada will be accepted as an Untis integration partner;
- that the family's school will activate a Platform Application;
- which modules and permissions the actual parent account has;
- whether the private iCal feed is enabled for that school/account;
- whether QR/TOTP credentials are available;
- that community-observed parent-account limitations apply universally;
- an official JSON-RPC shutdown date;
- legal advice on the processor/controller relationship;
- an accepted Ada runtime dependency or provider architecture.

These need either account-specific validation, vendor confirmation, product decisions or an ADR.

---

## 12. Sources

### Official Untis sources

Accessed 2026-09-23.

- [Untis Developer Portal — Getting started / Platform Applications](https://developer.untis.com/getting-started/overview/)
- [Getting a Platform Application](https://developer.untis.com/getting-started/get-platform-application/)
- [WebUntis APIs overview](https://developer.untis.com/api-reference/webuntis-apis/)
- [API overview / production endpoint / rate limit](https://developer.untis.com/api-reference/api-overview/)
- [Authentication model](https://developer.untis.com/core-concepts/authentication-model/)
- [Authorization model](https://developer.untis.com/core-concepts/authorization-model/)
- [Timetable data API](https://developer.untis.com/api-reference/webuntis-apis/timetable-data/)
- [Messaging API](https://developer.untis.com/api-reference/webuntis-apis/messaging/)
- [Untis integration privacy information](https://www.untis.at/en/privacy-policy-wu-integrations)
- [WebUntis support — JSON-RPC remains available](https://help.untis.at/hc/en-150/articles/22597731127708-New-web-addresses-for-WebUntis)
- [WebUntis release notes, including JSON-RPC/2FA restriction](https://help.untis.at/hc/en-150/articles/360008456699-WebUntis-Release-Notes)
- [WebUntis private iCal subscription](https://help.untis.at/hc/de/articles/360014979580-Wie-funktioniert-das-iCal-Kalender-Abonnement-in-WebUntis)

### Open-source projects / community evidence

Repository state inspected 2026-09-23.

- [python-webuntis](https://github.com/python-webuntis/python-webuntis)
- [SchoolUtils/WebUntis](https://github.com/SchoolUtils/WebUntis)
- [Community JSON-RPC sunset discussion — **not an official Untis announcement**](https://github.com/SchoolUtils/WebUntis/issues/123)
- [Home Assistant WebUntis integration](https://github.com/JonasJoKuJonas/homeassistant-WebUntis)
- [UntAPI](https://github.com/4biddencode/UntAPI)
- [Internal-REST Home Assistant proof/reference](https://github.com/Naumsede/webuntis-home-assistant)
- [UntisPlus](https://github.com/ninocss/UntisPlus)
