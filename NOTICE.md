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

## Adopted dependencies

- **PydanticAI 2.46.0** — MIT License. Used behind Ada's replaceable agent-runtime adapter.
- **httpx2 2.13.1** — BSD-3-Clause. Already in PydanticAI's dependency graph; pinned directly for Ada's proxy-independent local Ollama transport. Its redistribution is included in the release-artifact review below.
- **cedarpy 4.12.0** — Apache License 2.0. Community-maintained Python/PyO3 binding used only behind AdaGuard.
- **Cedar Policy engine 4.12.0** — Apache License 2.0. Embedded by cedarpy as the authorization engine selected by ADR-0004.

- **DBOS 3.0.0** — MIT License. Used behind Ada's durable-action port as the initial durable-execution substrate selected by ADR-0005.

Apache-2.0 components remain Apache-2.0. Ada's project-owned code remains MIT; third-party code is not relicensed as Ada MIT code. Required license and NOTICE material must be preserved when distribution obligations apply.

## Existing transitive license findings and release scope

The adopted top-level dependencies do not have an entirely permissive
transitive graph. In one **combined Ada + research candidates** installation
on macOS, the declared Ada requirements led to these reconstructed baseline
paths (the independently installed Ada-only graph remains to be checked):

| Path from Ada | Installed Mac example | Distribution review |
| --- | --- | --- |
| `dbos` → `psycopg` → `psycopg-binary` | 3.3.6 / 3.3.6, LGPL-3.0-only | The binary wheel bundles native client libraries, including `libpq` and OpenSSL. Inspect each exact platform wheel and its bundled licenses/source and applicable LGPL obligations before redistributing it. |
| `pydantic-ai-slim` → `tiktoken` → `requests` → `certifi` | 2026.7.22, MPL-2.0 | Review the actual certificate bundle and package notices/source access if included in an Ada-distributed artifact. |

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

## External local-model baseline

The first local-chat profile is designed to interoperate with separately installed software/model artifacts that are **not vendored or redistributed by Ada**:

- **Ollama** — MIT-licensed local model runtime/service. ADR-0006 proposes it as the initial self-hosted model-serving baseline.
- **Qwen3.5 9B / Ollama tag `qwen3.5:9b`** — externally downloaded Q4_K_M model artifact used as the current target-hardware baseline after a direct A/B test on Ada's MacBook Air M1 / 16 GB target. Ollama currently reports a 6.6 GB artifact and Apache License 2.0. Ada does not redistribute the weights.
- **Qwen3 8B / Ollama tag `qwen3:8b`** — earlier 5.2 GB target-hardware baseline retained as a tested fallback; Apache License 2.0. Ada does not redistribute the weights.

Model tags and artifacts can change independently from Ada. Reproducible model artifact pinning/distribution remains an explicit open constraint before Ada distributes or automatically provisions model weights.

When a third-party component is adopted or upgraded, add or update the required attribution/notices and exact reviewed version here before merge.
