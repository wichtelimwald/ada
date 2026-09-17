# Skill: Repository context efficiency

## Goal

Use the minimum repository context necessary to answer or implement correctly.

## Rules

- Start from the task and known architecture docs; do not scan the whole repository by default.
- Read exact files/ranges once the relevant location is known.
- Prefer repository indexes only when they materially reduce context cost.
- ProjectAtlas and Graphify are candidates for later evaluation, not current runtime or developer dependencies.
- Do not install, initialize, or execute either tool solely because this skill mentions it.
- If one is adopted, record provenance, installation method, privacy behavior, generated artifacts, and gitignore rules.

For a small repository, targeted source inspection is the preferred default.
