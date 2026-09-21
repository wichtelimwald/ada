from __future__ import annotations

from pathlib import Path
import site


def main() -> int:
    candidates = [Path(path) / "ctparse" / "ctparse.py" for path in site.getsitepackages()]
    target = next((path for path in candidates if path.exists()), None)
    if target is None:
        raise SystemExit("ctparse/ctparse.py not found in this environment")

    text = target.read_text(encoding="utf-8")
    old_import = "from .scorer import Scorer\n"
    new_import = "from .scorer import Scorer, DummyScorer\n"
    old_default = "_DEFAULT_SCORER = load_default_scorer()"
    new_default = "_DEFAULT_SCORER = DummyScorer()"

    if old_import not in text or old_default not in text:
        raise SystemExit("quickadd source shape changed; refusing to patch silently")

    text = text.replace(old_import, new_import, 1)
    text = text.replace(old_default, new_default, 1)
    target.write_text(text, encoding="utf-8")
    print(f"patched {target} to avoid import-time pickle model loading")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
