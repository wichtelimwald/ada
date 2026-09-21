from __future__ import annotations

from pathlib import Path
import site


def main() -> int:
    candidates = [Path(path) / "ctparse" / "ctparse.py" for path in site.getsitepackages()]
    target = next((path for path in candidates if path.exists()), None)
    if target is None:
        raise SystemExit("ctparse/ctparse.py not found in this environment")

    text = target.read_text(encoding="utf-8")
    old = """    except CTParseTimeoutError:
        logger.debug('Timeout on "{}"'.format(txt))
        return
"""
    new = """    except CTParseTimeoutError:
        logger.debug('Timeout on "{}"'.format(txt))
        raise
"""

    if old not in text:
        raise SystemExit(
            "quickadd timeout source shape changed; refusing to patch silently"
        )

    text = text.replace(old, new, 1)
    target.write_text(text, encoding="utf-8")
    print(f"patched {target} to surface CTParseTimeoutError for research")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
