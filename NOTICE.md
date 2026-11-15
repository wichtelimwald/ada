# Notices and third-party status

Ada's project-owned source code and project-authored repository guidance are licensed under MIT unless a file explicitly states otherwise.

## Current repository state

At this stage, no third-party runtime source code, model weights, assets, prompts, or skill text are vendored into this repository.

Ada-specific repository guidance is project-authored unless explicitly attributed below. References to external projects describe inspiration, research candidates, or development practices; they do not imply dependency adoption, endorsement, or redistribution.

## Guidance provenance

- **UX design guidance** — Ada's concise `.github/skills/ux-design.md` was written for this project after reviewing Emil Kowalski's `apple-design` skill from `emilkowalski/skills` (MIT). Ada does not vendor that skill's text; this attribution is retained to make the design influence and provenance explicit.

## License evaluation policy

Before adopting or distributing any third-party component, record separately:

1. **Code license** and obligations.
2. **Model / weight / voice / asset license**, when applicable.
3. **Usage or distribution restrictions**, including commercial-use limits, attribution, network-copyleft, trademark, data-use, or hosted-service terms.
4. **Transitive dependencies and bundled artifacts** that materially affect distribution.

Permissive licenses such as MIT or Apache-2.0 are generally compatible candidates for Ada's MIT-owned code, subject to their notice/attribution requirements. Copyleft or network-copyleft components require an explicit compatibility and distribution-impact decision before adoption. Non-commercial material must not become Ada's code or asset base.

A software repository's license must never be assumed to cover separately distributed model weights, voices, datasets, fonts, images, or other assets.

## Mark LIV boundary

Mark LIV is licensed CC BY-NC 4.0 and is a product/UX inspiration only.

For Ada development:

- It is acceptable to document independently observed product behavior and general interaction requirements.
- Do not copy Mark LIV source code or assets into Ada.
- Do not paste Mark LIV source code or assets into AI-agent/chat contexts used to write Ada implementation code.
- Do not keep Mark LIV source code open as an implementation reference while writing equivalent Ada code.
- If Mark LIV material is quoted, shown, or otherwise reused in documentation where the license permits it, preserve the required CC BY attribution and clearly identify the source and modifications.

## Research-only unresolved artifact review

- **Acreom Quickadd / ctparse, pinned research commit `0b3bfc26a7347a80821e86eb3838556a7adc2a30`** — the repository code is MIT-licensed. Its bundled `ctparse/models/model.pbz` scorer is used only in the disposable research characterization/conversion path. The reviewed source/package metadata does not separately establish the model's origin, training-data provenance, or redistribution terms. Ada therefore does not vendor or redistribute the scorer or its transformed JSON form, and the artifact license/provenance gate remains **CONDITIONAL** pending explicit evidence.

## Experimental optional dependency — not production-approved

- **kdbxtool 0.1.7** — Apache-2.0 (upstream [PyPI](https://pypi.org/project/kdbxtool/0.1.7/), [source at published commit](https://github.com/coreyleavitt/kdbxtool/tree/fa5c6bfc1522474e44e764bb82e1711abf012d3a)). An optional PoC and dedicated offline credential-runtime *candidate* use it for KDBX4 reading. **Not production-approved** and no code vendored. Upstream classifies the package as alpha; release-wheel SHA-256 and PyPI publish attestation are recorded in the [reader evaluation](docs/research/kdbx-reader-evaluation.md). A target synthetic KeePassXC unlock passed. An independent Claude agent reviewed the full PR and 49 wheel artifacts; this is not human security certification or authorization for real credentials. See the [synthetic-only closure and residual-risk record](docs/plans/credential-release-hardening.md).
- **Pinned runtime graph (candidate):** [`requirements/ada-runtime-py314-linux-aarch64.txt`](requirements/ada-runtime-py314-linux-aarch64.txt) pins all **49** CPython 3.14/Linux aarch64 external wheels (including `setuptools`), with SHA-256 verification and an exact base-image digest in [`Dockerfile.credentials`](Dockerfile.credentials). The earlier [seven KDBX wheel pins](requirements/kdbx-py314-linux-aarch64.txt) remain unchanged for the research path. The previous target Docker image build, `pip check`, package inventory and synthetic unlock passed; for the three-wheel security refresh and Debian zlib patch, the operator reported a passing target rebuild, offline smoke, Grype re-scan and full Python suite on 2026-11-15 (exact Git SHA not printed). Integrity pinning does **not** establish absence of vulnerabilities, malicious code, license obligations or problematic bundled native libraries.
- **Transitive license metadata (PyPI, preliminary):** `argon2-cffi==25.1.0` — MIT; `argon2-cffi-bindings==26.2.0` — MIT (bundles Argon2 under CC0); `cffi==2.1.1` — MIT-0; `pycparser==3.12` — BSD-3-Clause; `pycryptodomex==3.24.2` — BSD / public domain; `defusedxml==0.7.1` — Python Software Foundation License. See each package's [PyPI project metadata](https://pypi.org/) and inspect the **exact shipped wheel contents and license files** before any distribution. Some exact version/wheel artifacts have no PyPI provenance attestation; lack of attestation is neither proof of compromise nor verification of safety.
- **Distribution/security gates open:** review the exact 49-wheel/Linux image artifact, bundled native libraries, notices and known vulnerabilities; independent security review is required. The upstream KDBX4 reader verifies HMACs before `gzip.decompress()`, but decompression has **no expanded-size ceiling**. A 1-GiB runtime cgroup bounds the blast radius; target testing on 2026-11-15 confirmed a 1,280 MiB authenticated synthetic payload triggers a container-scoped OOM kill (exit 137). Credential-runtime availability remains exposed to maliciously oversized *authenticated* vaults. No experimental or credential image may be published as a vetted runtime.
- **PyKeePass 4.2.0** — GPL-3.0; evaluated but not integrated. **KeePassXC CLI** — separately installed GPL application/CLI, potential fallback, not bundled into Ada.

See [KDBX reader evaluation](docs/research/kdbx-reader-evaluation.md).

## Adopted dependencies

- **PydanticAI 2.66.0** (`pydantic-ai-slim[openai]`) — MIT License. Used behind Ada's replaceable agent-runtime adapter. Updated from 2.46.0 after the 2026-11-15 scan; target validation is recorded above.
- **httpx2 2.13.1** — BSD-3-Clause. Already in PydanticAI's dependency graph; pinned directly for Ada's proxy-independent local Ollama transport. Its [focused dependency review](docs/research/httpx2-direct-transport-review.md) records provenance, maintenance, privacy, security advisories, the installed wheel license, and transitive scope. Redistributing Ada-built images/installers still requires the separate release-artifact review below.
- **cedarpy 4.12.0** — Apache License 2.0. Community-maintained Python/PyO3 binding used only behind AdaGuard.
- **Cedar Policy engine 4.12.0** — Apache License 2.0. Embedded by cedarpy as the authorization engine selected by ADR-0004.

- **DBOS 3.0.0** — MIT License. Used behind Ada's durable-action port as the initial durable-execution substrate selected by ADR-0005.

- **icalendar 7.3.0** — BSD-2-Clause (Plone Foundation). RFC 5545 parsing/serialization for the CalDAV adapter (ADR-0009, MVP-60). Its [focused dependency review](docs/research/caldav-parsing-dependencies-review.md) records provenance, the two closed DoS advisories (both fixed below the adopted version), the installed wheel license, and transitive scope (`tzdata` Apache-2.0; `python-dateutil`/`six` already resolved).
- **recurring-ical-events 3.8.2** — LGPL-3.0-or-later. Client-side recurrence expansion for the CalDAV read path, used unmodified as a separately installed package (decision D1, MVP-60 step plan). Same LGPL obligation class as the existing `psycopg-binary` path below; see the [dependency review](docs/research/caldav-parsing-dependencies-review.md) for the distribution-obligation analysis.
- **x-wr-timezone 2.0.1** — LGPL-3.0-or-later. Direct dependency of `recurring-ical-events`; same review and obligations.

Apache-2.0 components remain Apache-2.0. Ada's project-owned code remains MIT; third-party code is not relicensed as Ada MIT code. Required license and NOTICE material must be preserved when distribution obligations apply.

## Existing transitive license findings and release scope

The adopted top-level dependencies do not have an entirely permissive
transitive graph. In one **combined Ada + research candidates** installation
on macOS, the declared Ada requirements led to these reconstructed baseline
paths (the independently installed Ada-only graph remains to be checked):

| Path from Ada | Installed Mac example | Distribution review |
| --- | --- | --- |
| `dbos` → `psycopg` → `psycopg-binary` | Historical Mac 3.3.6; locked Linux/aarch64 image **3.3.9**, LGPL-3.0-only | The independent PR #60 review found **14 bundled native libraries**, including libpq, OpenSSL, Kerberos and LDAP, not covered by the Grype scan and with incomplete included notices. Do not treat these libraries as CVE- or license-cleared: review before credential-runtime DBOS/psycopg imports or redistribution of a prebuilt image. |
| `pydantic-ai-slim` → `tiktoken` → `requests` → `certifi` | 2026.7.22, MPL-2.0 | Review the actual certificate bundle and package notices/source access if included in an Ada-distributed artifact. |
| Ada → `recurring-ical-events` (direct) | 3.8.2, LGPL-3.0-or-later | Pure-Python wheel, used unmodified. Confirm LGPL sections 4/5 (source availability, replaceability) are satisfied before any prebuilt image/installer bundles it; see the [dependency review](docs/research/caldav-parsing-dependencies-review.md). |
| Ada → `recurring-ical-events` → `x-wr-timezone` | 2.0.1, LGPL-3.0-or-later | Same obligation as above; same review. |

These paths explain why direct MIT/Apache-2.0 licenses alone did not close the
earlier license gate. Installed Mac file names and package metadata do not
establish compliance for a Linux image, and the combined environment is not
an independent Ada-only resolution. No incompatibility with Ada-owned MIT
code has been established from this evidence; distribution compliance remains
unverified. See [Psycopg's binary-install documentation](https://www.psycopg.org/psycopg3/docs/basic/install.html),
the [LGPLv3 terms](https://www.gnu.org/licenses/lgpl-3.0.html), and the
[MPL 2.0 distribution FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).

The initial release plan is Ada-owned source code plus the dependency manifest
and Dockerfile for users to build locally. Ada does not currently publish a
prebuilt runtime image or installer bundling those dependencies. Review the
resolved Ada-only dependency graph and appropriate project notices before a
source release. Any future Ada-built image or installer needs its own review
of the exact release artifacts, license and copyright notices, covered-source
availability, bundled native libraries, and applicable LGPL conditions
**before publication**. A one-line notice is not sufficient evidence for
that distribution mode. Model artifacts remain separately installed as
described above.

## External Memory-history prerequisite

- **Git CLI** — the MVP-20 development Memory history adapter interoperates with a separately installed Git executable. The Git project is distributed under GPLv2. Ada does not vendor, bundle, or redistribute Git, and Git history is not an authentication or authorization boundary. Any future Ada installer/image that includes Git requires a separate artifact-level license/distribution review before publication. See [ADR-0010](docs/decisions/ADR-0010-memory-write-history.md).

## External local-model baseline

The first local-chat profile is designed to interoperate with separately installed software/model artifacts that are **not vendored or redistributed by Ada**:

- **Ollama** — MIT-licensed local model runtime/service. ADR-0006 accepts it as the initial self-hosted model-serving baseline.
- **Qwen3.5 9B / Ollama tag `qwen3.5:9b`** — externally downloaded Q4_K_M model artifact used as the current target-hardware baseline after a direct A/B test on Ada's MacBook Air M1 / 16 GB target. Ollama currently reports a 6.6 GB artifact and Apache License 2.0. Ada does not redistribute the weights.
- **Qwen3 8B / Ollama tag `qwen3:8b`** — earlier 5.2 GB target-hardware baseline retained as a tested fallback; Apache License 2.0. Ada does not redistribute the weights.

Model tags and artifacts can change independently from Ada. Reproducible model artifact pinning/distribution remains an explicit open constraint before Ada distributes or automatically provisions model weights.

When a third-party component is adopted or upgraded, add or update the required attribution/notices and exact reviewed version here before merge.
