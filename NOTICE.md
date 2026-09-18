# Notices and third-party status

Ada's project-owned source code and project-authored repository guidance are licensed under MIT unless a file explicitly states otherwise.

## Current repository state

At this stage, no third-party runtime source code, model weights, assets, prompts, or skill text are vendored into this repository.

Content under `.github/` and Ada-specific prompt/agent documentation is original project content. References to external projects describe inspiration, research candidates, or development practices; they do not imply copying, dependency adoption, endorsement, or redistribution.

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

None yet.

When a third-party component is adopted, add the required attribution/notices and exact reviewed version here before merge.
