#!/usr/bin/env python3
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for name in ("reme", "langmem", "hindsight", "letta"):
    p = root / name / "candidate.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except Exception as exc:
            data = {"candidate": name, "status": "FINDING", "notes": [f"invalid candidate.json: {exc}"]}
    else:
        data = {"candidate": name, "status": "BLOCKED", "notes": ["candidate runner did not produce candidate.json"]}
    rows.append(data)

payload = {"result_dir": str(root), "candidates": rows}
(root / "comparison.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
lines = [
    "# Ada Memory four-candidate characterization",
    "",
    "This is characterization evidence, not a ranking or architecture decision.",
    "",
    "| Candidate | Run | Authoritative form | Rebuild/Edit | Forget | Isolation | Semantic artifact |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
for r in rows:
    sub = r.get("substrate", {})
    art = r.get("semantic_artifact", "") or "—"
    lines.append(
        f"| {r.get('candidate','?')} | {r.get('status','?')} | {sub.get('authority','?')} | "
        f"{sub.get('rebuild','?')} | {sub.get('forget','?')} | {sub.get('isolation','?')} | {art} |"
    )
lines += ["", "## Notes", ""]
for r in rows:
    lines.append(f"### {r.get('candidate','?')}")
    for note in r.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")
(root / "SUMMARY.md").write_text("\n".join(lines))
print(root / "SUMMARY.md")
