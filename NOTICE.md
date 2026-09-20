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

## Adopted dependencies

- **PydanticAI 2.46.0** — MIT License. Used behind Ada's replaceable agent-runtime adapter.
- **cedarpy 4.12.0** — Apache License 2.0. Community-maintained Python/PyO3 binding used only behind AdaGuard.
- **Cedar Policy engine 4.12.0** — Apache License 2.0. Embedded by cedarpy as the authorization engine selected by ADR-0004.

## Accepted dependency pending implementation

- **DBOS 3.0.0** — MIT License. Accepted by ADR-0005 as Ada's initial durable-execution substrate behind Ada-owned action/outcome semantics. It is not yet a runtime dependency in the production scaffold.

Apache-2.0 components remain Apache-2.0. Ada's project-owned code remains MIT; third-party code is not relicensed as Ada MIT code. Required license and NOTICE material must be preserved when distribution obligations apply.

When a third-party component is adopted or upgraded, add or update the required attribution/notices and exact reviewed version here before merge.
