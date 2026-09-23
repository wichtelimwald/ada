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
misattributes a manual edit, a synthetic index lock blocks capture, a
stale Ada write loses an intervening edit, a shared-to-private move leaves
the content in shared Git history, and a changed claim can retain an old
source while independent claims remain unlabelled. A separate, path-scoped
external capture is demonstrated as a research example, not an automatic
watcher or concurrency-safe production write path. In real code, serialize
writes, compare the content read before every write, use a durable atomic
replacement, stop on Git lock failures, and reconcile after crashes. Never
delete an unexplained Git lock automatically. Do not allow scope narrowing
until the affected history, backups and readers can be handled under an
explicit policy. None of these operational gates are closed by this control.

For a backend decision, compare this control with the ReMe/LangMem run on
the target Mac using representative vaults and queries. A score must not be
filled in for unmeasured recall, automatic edit capture, or protection-domain
enforcement. Accept a first Memory ADR only after its chosen release scope
and the remaining mandatory boundaries are explicit.
