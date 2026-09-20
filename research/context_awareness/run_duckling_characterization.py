from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _minute_local(value: str, timezone_name: str) -> str:
    from zoneinfo import ZoneInfo

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        parsed.astimezone(ZoneInfo(timezone_name))
        .replace(tzinfo=None, second=0, microsecond=0)
        .isoformat(timespec="minutes")
    )


def _wall_time_status(local_iso: str, zone_name: str) -> str:
    from zoneinfo import ZoneInfo

    naive = datetime.fromisoformat(local_iso)
    zone = ZoneInfo(zone_name)
    candidates = []
    for fold in (0, 1):
        aware = naive.replace(tzinfo=zone, fold=fold)
        round_trip = aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
        candidates.append((round_trip == naive, aware.utcoffset()))

    valid = [item for item in candidates if item[0]]
    if not valid:
        return "nonexistent"
    if len(valid) == 2 and valid[0][1] != valid[1][1]:
        return "ambiguous"
    return "valid"


def _normalize_duckling(
    raw_results: list[dict[str, Any]],
    timezone_name: str,
) -> dict[str, Any] | None:
    time_results = [item for item in raw_results if item.get("dim") == "time"]
    if not time_results:
        return None

    item = time_results[0]
    value = item.get("value") or {}
    value_type = value.get("type")

    if value_type == "value" and isinstance(value.get("value"), str):
        local = _minute_local(value["value"], timezone_name)
        return {
            "kind": "point",
            "local": local,
            "wall_time_status": _wall_time_status(local, timezone_name),
            "grain": value.get("grain"),
            "body": item.get("body"),
            "latent": item.get("latent"),
        }

    if value_type == "interval":
        start = (value.get("from") or {}).get("value")
        end = (value.get("to") or {}).get("value")
        if isinstance(start, str) and isinstance(end, str):
            local_start = _minute_local(start, timezone_name)
            local_end = _minute_local(end, timezone_name)
            return {
                "kind": "interval",
                "start": local_start,
                "end": local_end,
                "start_wall_time_status": _wall_time_status(local_start, timezone_name),
                "end_wall_time_status": _wall_time_status(local_end, timezone_name),
                "body": item.get("body"),
                "latent": item.get("latent"),
            }

    return {
        "kind": "other",
        "body": item.get("body"),
        "latent": item.get("latent"),
        "raw_value": value,
    }


def _matches_expected(
    actual: dict[str, Any] | None,
    expected: dict[str, Any] | None,
) -> bool | None:
    if expected is None:
        return None
    if actual is None:
        return False
    return all(actual.get(key) == value for key, value in expected.items())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("cases.json"),
    )
    args = parser.parse_args()

    context = json.loads(args.cases.read_text(encoding="utf-8"))
    reference = datetime.fromisoformat(context["reference"])
    reference_ms = int(reference.timestamp() * 1000)

    rows = []
    for case in context["cases"]:
        form = urlencode(
            {
                "text": case["expression"],
                "lang": "de",
                "locale": "de_DE",
                "dims": '["time"]',
                "tz": context["timezone"],
                "reftime": str(reference_ms),
                "latent": "false",
            }
        ).encode("utf-8")
        request = Request(
            args.base_url.rstrip("/") + "/parse",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            raw = json.loads(response.read().decode("utf-8"))
        actual = _normalize_duckling(raw, context["timezone"])

        rows.append(
            {
                "id": case["id"],
                "group": case["group"],
                "expression": case["expression"],
                "expected": case.get("expected"),
                "actual": actual,
                "matches_expected": _matches_expected(
                    actual,
                    case.get("expected"),
                ),
                "error": None,
                "raw": raw,
            }
        )

    payload = {
        "backend": "duckling",
        "source_commit": "59a13ff87b1aa8be6b93d387244f8636b26185c5",
        "reference": context["reference"],
        "timezone": context["timezone"],
        "locale": "de_DE",
        "results": rows,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
