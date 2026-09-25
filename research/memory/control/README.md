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
and the persistence of deleted content in Git history. This matches ADR-0008's
accepted distinction: Ada must stop retrieving a forgotten note from current
Memory and derived indexes; historical versions may remain available for
recovery, with permanent purge handled separately. **A successful run does
not prove derived-index forgetting, privacy, or retrieval quality.** The
output lists those unsolved gates explicitly. Git commit author fields in
this fixture are synthetic and do not authenticate a real editor.

The same script also runs five **failure probes**: unscoped Git staging
misattributes a manual edit, a synthetic index lock blocks history capture
after a file write, a stale Ada read can overwrite an intervening editor
change, a shared-to-private move leaves the old content in shared Git history,
and plain Markdown/direct search does not automatically retire stale sources,
label contradictions, or exclude superseded text from retrieval. A
path-restricted commit example deliberately leaves an unrelated pre-staged
editor change out of Ada's commit.

These probes demonstrate failure modes of the simple control; they do not
supply a production-safe write path. In real code, serialize Ada writes,
compare the content read before every Ada write, use a durable atomic
replacement, restrict commits to the intended path or a separate verified
index, stop on Git lock failures, capture Ada writes promptly so later manual
reverts remain visible, and reconcile after crashes. Never delete an
unexplained Git lock automatically.

Narrowing a note from shared to private may stop **future current-state
sharing**, but it cannot revoke content already read, synced, copied, backed
up, or retained in shared history. Ada must warn about that non-revocation
boundary. Historical purge is a separate optional operation/policy, not a
precondition that makes scope narrowing permanently impossible. None of these
operational gates are closed by this control.

For a backend decision, compare this control with the ReMe/LangMem run on
the target Mac using representative vaults and queries. A score must not be
filled in for unmeasured recall, automatic edit capture, or protection-domain
enforcement. Accept a first Memory ADR only after its chosen release scope
and the remaining mandatory boundaries are explicit.
