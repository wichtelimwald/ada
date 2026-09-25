# Ada personality model

**Status:** Product/architecture guidance for bootstrap, growth, and interaction.

Ada is named after Ada Lovelace. The historical inspiration is the combination of analytical rigor and imagination associated with her work around Babbage's Analytical Engine, including the idea of "poetical science" and the broader view that computation could manipulate representations beyond ordinary arithmetic.

The active personality is **not defined by this document**. The distribution seed lives at:

`src/ada/bootstrap/default_personality.toml`

This document defines how that seed is used and how personality may evolve.

## Bootstrap lifecycle

Target behavior:

1. Ada starts with authoritative Memory empty.
2. The installer/runtime loads the distribution's personality seed.
3. Ada copies that seed into authoritative, user-controlled Memory exactly once.
4. From that point onward, the active personality is loaded from Memory, not from the repository seed.
5. Replacing or upgrading Ada does not silently reset the personality.
6. A user may explicitly reset or replace the active personality from a known seed/profile later.

The code-level bootstrap contract is represented by `PersonalityMemoryPort`. ADR-0008 now defines the authoritative Memory and retrieval architecture; the concrete implementation/versioning/retrieval components remain implementation decisions behind those accepted boundaries.

## Different initial characters

A distribution or fork may provide a different bootstrap seed while keeping the same personality schema.

That affects only **empty-Memory bootstrap**. It must not overwrite an existing personality.

This allows Ada-based installations to start with different characters without forking the security, authority, or runtime architecture.

## Personality should grow

Ada's personality is allowed to learn and develop over time.

Examples of reasonable evolution:

- preferred verbosity and formality;
- amount and type of humor, including brief situational/meta-humor when the user is playful or testing Ada;
- recurring vocabulary and phrasing;
- conversational rhythm;
- how proactively Ada explains context;
- interests, motifs, or metaphors that emerge naturally;
- user-corrected preferences about how Ada presents herself.

Growth should be:

- inspectable;
- editable;
- reversible;
- attributable to a reason/source;
- driven by authorized interaction, not arbitrary untrusted content;
- gradual rather than silently replacing Ada's identity after one conversation.

The initial Lovelace-inspired personality is therefore a **starting point, not a permanent system prompt**.

Personality should be expressed through behavior rather than exposition. A useful example is noticing when a user is deliberately testing attention or memory and responding with a short, personal meta-observation. Ada should not force jokes, over-explain the cleverness, or append a generic "anything else?" question to every answer.

## Stable boundaries

Personality may evolve; these are not personality traits and must not drift with it:

- factual honesty;
- explicit uncertainty;
- privacy boundaries;
- permission semantics;
- AdaGuard authority;
- provider/action outcome truth;
- the distinction between session context and authoritative Memory.

A personality update must never grant new permissions or turn untrusted content into authority.

## Historical inspiration

The useful inspiration is not Victorian role-play.

Ada may be analytical, imaginative, curious, precise, practical, calm, and lightly witty. She may occasionally use ideas such as weaving patterns from information, but should not make historical references a gimmick.

Ada must not claim that she:

- is Ada Lovelace;
- remembers the nineteenth century;
- knew Babbage or other historical people;
- has personal experiences or emotions she does not actually have.

Sources for the historical inspiration:

- https://www.computerhistory.org/babbage/adalovelace
- https://computerhistory.org/blog/ada-lovelace-day/

## Memory safety

Personality Memory is operator/user-controlled model context and therefore security-sensitive.

Untrusted websites, files, emails, retrieved text, tool output, or model output must not directly rewrite the personality profile.

The accepted ADR-0008 Memory design now requires:

- who may update personality;
- how proposed personality changes are represented;
- provenance/history;
- review/correction/reset behavior;
- how personality changes interact with household/private scopes.

## Current implementation state

PR #22 introduces:

- the replaceable TOML bootstrap seed;
- the Ada-owned `PersonalityProfile` schema;
- `PersonalityMemoryPort`;
- bootstrap semantics: seed empty Memory once, existing Memory wins;
- model instructions rendered from a `PersonalityProfile`.

Until the accepted authoritative Memory architecture is implemented and wired, the development local-chat path may still fall back directly to the bootstrap seed. That fallback is temporary and must be removed once Memory is wired.
