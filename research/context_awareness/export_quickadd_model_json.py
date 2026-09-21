from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # This research conversion intentionally imports the pinned upstream package,
    # which performs its existing pickle load. The exported artifact contains
    # only primitive JSON data and is used to test a no-pickle runtime path.
    from ctparse.ctparse import _DEFAULT_SCORER

    model = _DEFAULT_SCORER._model
    payload = {
        "schema_version": 1,
        "ngram_range": list(model.transformer.ngram_range),
        "vocabulary": model.transformer.vocabulary,
        "alpha": model.estimator.alpha,
        "class_prior": list(model.estimator.class_prior),
        "log_likelihood": model.estimator.log_likelihood,
    }
    args.output.write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    print(f"exported safe JSON scorer model to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
