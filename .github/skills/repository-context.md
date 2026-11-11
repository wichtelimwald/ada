# Skill: Repository context efficiency

## Goal

Use the minimum repository context necessary to answer or implement correctly.

## Rules

- Start from the task and known architecture docs; do not scan the whole repository by default.
- Read exact files/ranges once the relevant location is known.
- Prefer repository indexes only when they materially reduce context cost.
- Do not install or initialize third-party indexing tools merely to inspect repository context. Evaluate provenance, privacy, licensing, and generated artifacts before adopting new tools.

For a small repository, targeted source inspection is the preferred default.
