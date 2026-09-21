from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import sys
from typing import Any, Callable
from zoneinfo import ZoneInfo


def _minute_iso(value: datetime) -> str:
    return value.replace(second=0, microsecond=0, tzinfo=None).isoformat(timespec="minutes")


def _wall_time_status(local_iso: str, zone_name: str) -> str:
    """Classify a local wall time using only stdlib zoneinfo."""

    naive = datetime.fromisoformat(local_iso)
    zone = ZoneInfo(zone_name)
    candidates: list[tuple[bool, Any]] = []
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


def _normalize_point(value: datetime, zone_name: str) -> dict[str, Any]:
    local = _minute_iso(value)
    return {
        "kind": "point",
        "local": local,
        "wall_time_status": _wall_time_status(local, zone_name),
    }


def _run_dateparser(
    expression: str,
    context: dict[str, Any],
    date_data_parser: Any,
) -> dict[str, Any] | None:
    reference = datetime.fromisoformat(context["reference"]).replace(tzinfo=None)
    locale = context["locale"]
    languages = [locale.split("-")[0], "en"]
    parser = date_data_parser(
        languages=languages,
        use_given_order=True,
        settings={
            "RELATIVE_BASE": reference,
            "PREFER_DATES_FROM": context["policy"]["prefer_dates_from"],
            "DATE_ORDER": context["policy"]["date_order"],
            "PREFER_LOCALE_DATE_ORDER": False,
            "RETURN_AS_TIMEZONE_AWARE": False,
            "RETURN_TIME_AS_PERIOD": True,
        },
    )
    data = parser.get_date_data(expression)
    parsed = data.date_obj
    if parsed is None:
        return None
    result = _normalize_point(parsed, context["timezone"])
    if data.period in {"year", "month", "week", "day"}:
        result["semantic_kind"] = "date"
        result["granularity"] = data.period
    elif data.period == "time":
        result["semantic_kind"] = "datetime"
        result["granularity"] = "minute"
    result["parser_period"] = data.period
    result["parser_locale"] = data.locale
    return result


def _time_to_local(value: Any) -> str | None:
    if value is None:
        return None
    if value.year is None or value.month is None or value.day is None:
        return None
    return datetime(
        value.year,
        value.month,
        value.day,
        value.hour or 0,
        value.minute or 0,
    ).isoformat(timespec="minutes")


def _time_semantics(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    has_date = (
        value.year is not None
        and value.month is not None
        and value.day is not None
    )
    has_time = value.hour is not None
    if has_date and not has_time:
        return "date", "day"
    if has_date and has_time:
        return "datetime", "minute" if value.minute is not None else "hour"
    if has_time:
        return "time", "minute" if value.minute is not None else "hour"
    return None, None


def _run_quickadd(
    expression: str,
    context: dict[str, Any],
    ctparse_func: Callable[..., Any],
) -> dict[str, Any] | None:
    reference = datetime.fromisoformat(context["reference"]).replace(tzinfo=None)
    parsed = ctparse_func(
        expression,
        ts=reference,
        date_format="EU",
        pm_bias=False,
        fallback=False,
        latent_time=True,
    )
    if parsed is None or parsed.resolution is None:
        return None

    resolution = parsed.resolution
    kind = type(resolution).__name__

    if kind == "Time":
        local = _time_to_local(resolution)
        semantic_kind, granularity = _time_semantics(resolution)
        if local is None:
            return {
                "kind": "partial",
                "semantic_kind": semantic_kind,
                "granularity": granularity,
                "raw_type": kind,
                "raw": str(resolution),
            }
        return {
            "kind": "point",
            "semantic_kind": semantic_kind,
            "granularity": granularity,
            "local": local,
            "wall_time_status": _wall_time_status(local, context["timezone"]),
        }

    if kind == "Interval":
        start = _time_to_local(resolution.start)
        end = _time_to_local(resolution.end)
        start_kind, start_granularity = _time_semantics(resolution.start)
        end_kind, end_granularity = _time_semantics(resolution.end)
        result: dict[str, Any] = {
            "kind": "interval",
            "start": start,
            "end": end,
            "start_semantic_kind": start_kind,
            "end_semantic_kind": end_kind,
            "start_granularity": start_granularity,
            "end_granularity": end_granularity,
        }
        if start is not None:
            result["start_wall_time_status"] = _wall_time_status(
                start, context["timezone"]
            )
        if end is not None:
            result["end_wall_time_status"] = _wall_time_status(
                end, context["timezone"]
            )
        return result

    if kind == "Duration":
        target = resolution.time(reference)
        local = _time_to_local(target)
        if local is None:
            return {"kind": "duration", "raw": str(resolution)}
        return {
            "kind": "point",
            "semantic_kind": "datetime",
            "granularity": "minute",
            "local": local,
            "wall_time_status": _wall_time_status(local, context["timezone"]),
            "source_kind": "duration",
            "raw": str(resolution),
        }

    if kind in {"Recurring", "RecurringArray"}:
        return {
            "kind": "recurring",
            "raw_type": kind,
            "raw": str(resolution),
        }

    return {
        "kind": "other",
        "raw_type": kind,
        "raw": str(resolution),
    }


def _backend_version(backend: str) -> str:
    package = "dateparser" if backend == "dateparser" else "quickadd"
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "unknown"


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
    parser.add_argument(
        "--backend",
        choices=("dateparser", "quickadd", "quickadd-safe", "quickadd-json"),
        required=True,
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("cases.json"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a compact pass/fail summary in addition to writing JSON.",
    )
    parser.add_argument(
        "--require-all-expected",
        action="store_true",
        help="Fail when any case with an explicit expected value does not match.",
    )
    args = parser.parse_args()

    context = json.loads(args.cases.read_text(encoding="utf-8"))

    timeout_error_type: type[Exception] | None = None
    if args.backend == "dateparser":
        from dateparser.date import DateDataParser

        run_backend = lambda expression, ctx: _run_dateparser(
            expression,
            ctx,
            DateDataParser,
        )
    else:
        from ctparse import ctparse
        from ctparse.timers import CTParseTimeoutError

        timeout_error_type = CTParseTimeoutError
        run_backend = lambda expression, ctx: _run_quickadd(
            expression,
            ctx,
            ctparse,
        )

    results = []
    for case in context["cases"]:
        try:
            actual = run_backend(case["expression"], context)
            error = None
        except Exception as exc:
            if timeout_error_type is not None and isinstance(exc, timeout_error_type):
                actual = None
                error = f"timeout: {type(exc).__name__}: {exc}"
            else:
                raise
        results.append(
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
                "error": error,
                "note": case.get("note"),
            }
        )

    payload = {
        "backend": args.backend,
        "version": _backend_version(args.backend),
        "reference": context["reference"],
        "timezone": context["timezone"],
        "locale": context["locale"],
        "policy": context["policy"],
        "results": results,
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    scored = [item for item in results if item["expected"] is not None]
    passed = [item for item in scored if item["matches_expected"] is True]
    failed = [item for item in scored if item["matches_expected"] is not True]
    errors = [item for item in results if item["error"] is not None]

    if args.summary:
        print(f"{args.backend:<15} {len(passed)}/{len(scored)} expected cases")
        if failed:
            print("  mismatches: " + ", ".join(item["id"] for item in failed))
        if errors:
            print(
                "  input errors/timeouts: "
                + ", ".join(item["id"] for item in errors)
            )

    if args.require_all_expected and failed:
        print(
            f"ERROR: {args.backend} failed {len(failed)} explicitly expected case(s).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
