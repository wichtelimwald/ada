# Minimal Markdown + Git + direct-search control

This **research-only** control exercises the simplest architecture in
ADR-0008 against the same synthetic preference, explicit correction,
unresolved conflict, and direct-edit scenarios used by the ReMe + LangMem
characterization. It uses Python's standard library and local Git; it adds
no Ada runtime dependency or production Memory implementation.

From the repository root:

```sh
python3 research/memory/control/run.py
```

The script creates three temporary Git repositories for two private domains
and one shared domain, then discards them. It uses synthetic text only. Its
assertions check current-file authority, basic search, a captured direct edit,
and the persistence of deleted content in Git history. **A successful run is
not a privacy, forgetting, or retrieval-quality PASS.** The output lists
those unsolved gates explicitly. Git commit author fields in this fixture
are synthetic and do not authenticate a real editor.

For a backend decision, compare this control with the ReMe/LangMem run on
the target Mac using representative vaults and queries. A score must not be
filled in for unmeasured recall, automatic edit capture, or protection-domain
enforcement. Accept a first Memory ADR only after its chosen release scope
and the remaining mandatory boundaries are explicit.
