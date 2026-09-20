from __future__ import annotations

import argparse
import json
from pathlib import Path
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
            for key in ("kind", "start", "end")
        }
    return value


def _state(left: Any, right: Any) -> str:
    if left is None and right is None:
        return "unresolved"
    if left is None or right is None:
        return "degraded_single_resolver"
    if _semantic_view(left) == _semantic_view(right):
        return "agreement"
    return "interpretation_conflict"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
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
        rows.append(
            {
                "id": case_id,
                "group": left_item.get("group") or right_item.get("group"),
                "expression": (
                    left_item.get("expression")
                    or right_item.get("expression")
                ),
                "state": _state(left_actual, right_actual),
                left["backend"]: left_actual,
                right["backend"]: right_actual,
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
        "interpretation_conflict": 0,
        "degraded_single_resolver": 1,
        "unresolved": 2,
        "agreement": 3,
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
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
