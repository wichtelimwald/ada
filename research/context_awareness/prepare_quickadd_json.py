from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import site


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-json", type=Path, required=True)
    args = parser.parse_args()

    candidates = [Path(path) / "ctparse" / "ctparse.py" for path in site.getsitepackages()]
    target = next((path for path in candidates if path.exists()), None)
    if target is None:
        raise SystemExit("ctparse/ctparse.py not found in this environment")

    package_dir = target.parent
    model_target = package_dir / "model.safe.json"
    shutil.copyfile(args.model_json, model_target)

    text = target.read_text(encoding="utf-8")
    old_import = "from .scorer import Scorer\n"
    new_import = (
        "from .scorer import Scorer\n"
        "from .nb_scorer import NaiveBayesScorer\n"
        "from .count_vectorizer import CountVectorizer\n"
        "from .nb_estimator import MultinomialNaiveBayes\n"
        "from .pipeline import CTParsePipeline\n"
        "import json\n"
        "import os\n"
    )
    old_default = "_DEFAULT_SCORER = load_default_scorer()"
    new_default = """def _load_safe_json_scorer() -> NaiveBayesScorer:
    with open(
        os.path.join(os.path.dirname(__file__), "model.safe.json"),
        encoding="utf-8",
    ) as fd:
        data = json.load(fd)

    transformer = CountVectorizer(tuple(data["ngram_range"]))
    transformer.vocabulary = {
        str(key): int(value)
        for key, value in data["vocabulary"].items()
    }

    estimator = MultinomialNaiveBayes(alpha=float(data["alpha"]))
    estimator.class_prior = tuple(float(value) for value in data["class_prior"])
    estimator.log_likelihood = {
        key: [float(value) for value in values]
        for key, values in data["log_likelihood"].items()
    }

    return NaiveBayesScorer(CTParsePipeline(transformer, estimator))


_DEFAULT_SCORER = _load_safe_json_scorer()"""

    if old_import not in text or old_default not in text:
        raise SystemExit("quickadd source shape changed; refusing to patch silently")

    text = text.replace(old_import, new_import, 1)
    text = text.replace(old_default, new_default, 1)
    target.write_text(text, encoding="utf-8")
    print(f"patched {target} to use safe JSON scorer model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
