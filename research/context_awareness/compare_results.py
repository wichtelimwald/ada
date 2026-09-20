from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def _semantic_view(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    kind = value.get("kind")
    if kind == "point":
        return {
            key: value.get(key)
            for key in ("kind", "local", "wall_time_status")
        }
    if kind == "interval":
        return {
            key: value.get(key)
            for key in (
                "kind",
                "start",
                "end",
                "start_wall_time_status",
                "end_wall_time_status",
            )
        }
    return value


def _state(
    left: Any,
    right: Any,
    *,
    left_error: str | None,
    right_error: str | None,
) -> str:
    if left_error is not None or right_error is not None:
        return "input_error"
    if left is None and right is None:
        return "unresolved"
    if left is None or right is None:
        return "single_resolver_result"
    if _semantic_view(left) == _semantic_view(right):
        return "agreement"
    return "interpretation_conflict"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print only compact comparison counts.",
    )
    parser.add_argument(
        "--require-all-agreement",
        action="store_true",
        help="Fail unless every compared case is semantic agreement.",
    )
    args = parser.parse_args()

    left = json.loads(args.left.read_text(encoding="utf-8"))
    right = json.loads(args.right.read_text(encoding="utf-8"))
    left_by_id = {item["id"]: item for item in left["results"]}
    right_by_id = {item["id"]: item for item in right["results"]}

    rows = []
    for case_id in left_by_id.keys() | right_by_id.keys():
        left_item = left_by_id.get(case_id, {})
        right_item = right_by_id.get(case_id, {})
        left_actual = left_item.get("actual")
        right_actual = right_item.get("actual")
        left_error = left_item.get("error")
        right_error = right_item.get("error")
        rows.append(
            {
                "id": case_id,
                "group": left_item.get("group") or right_item.get("group"),
                "expression": (
                    left_item.get("expression")
                    or right_item.get("expression")
                ),
                "state": _state(
                    left_actual,
                    right_actual,
                    left_error=left_error,
                    right_error=right_error,
                ),
                left["backend"]: left_actual,
                right["backend"]: right_actual,
                f"{left['backend']}_error": left_error,
                f"{right['backend']}_error": right_error,
                "expected": (
                    left_item.get("expected")
                    or right_item.get("expected")
                ),
                f"{left['backend']}_matches_expected": left_item.get(
                    "matches_expected"
                ),
                f"{right['backend']}_matches_expected": right_item.get(
                    "matches_expected"
                ),
            }
        )

    order = {
        "input_error": 0,
        "interpretation_conflict": 1,
        "single_resolver_result": 2,
        "unresolved": 3,
        "agreement": 4,
    }
    rows.sort(key=lambda row: (order[row["state"]], row["id"]))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1

    payload = {
        "left": {
            "backend": left["backend"],
            "version": left["version"],
        },
        "right": {
            "backend": right["backend"],
            "version": right["version"],
        },
        "counts": counts,
        "results": rows,
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")

    if args.summary:
        print(f"{left['backend']} vs {right['backend']}")
        for state in (
            "agreement",
            "interpretation_conflict",
            "single_resolver_result",
            "input_error",
            "unresolved",
        ):
            if counts.get(state):
                print(f"  {state}: {counts[state]}")
    elif not args.output:
        print(rendered, end="")

    non_agreement = [row for row in rows if row["state"] != "agreement"]
    if args.require_all_agreement and non_agreement:
        print(
            "ERROR: semantic-equivalence gate failed: "
            f"{len(non_agreement)} case(s) are not agreement.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
