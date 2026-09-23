#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from hindsight_client import Hindsight

base_url, fixture_path, out_path = sys.argv[1:4]
ready_timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 420
fixtures = json.loads(Path(fixture_path).read_text())
run_reflect = os.environ.get("HINDSIGHT_COMPARE_REFLECT", "0") == "1"
out = Path(out_path)
out.mkdir(parents=True, exist_ok=True)
semantic_path = out / "semantic.json"
client = Hindsight(base_url=base_url, timeout=600)

for _ in range(ready_timeout):
    try:
        client.get_version()
        break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError("Hindsight API did not become ready")

mission = fixtures["instructions"] + " Keep source evidence inspectable. Do not turn memory into authorization."
result = {
    "meta": {
        "core_semantics_completed": False,
        "reflect_is_optional": True,
        "reflect_enabled": run_reflect,
    }
}


def save():
    semantic_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


def dump(response):
    return response.model_dump(mode="json") if hasattr(response, "model_dump") else str(response)


def bank(name):
    bid = "ada-memcmp-" + name
    client.create_bank(
        bank_id=bid,
        retain_mission=mission,
        observations_mission=mission,
        enable_observations=True,
        enable_reranking=False,
    )
    return bid


def retain(bid, content, doc):
    return client.retain(
        bid,
        content,
        document_id=doc,
        metadata={"source_id": doc},
        tags=["ada-memory-comparison"],
    )


def recall(bid, query):
    return dump(
        client.recall(
            bid,
            query,
            types=["world", "experience", "observation"],
            include_source_facts=True,
            prefer_observations=True,
            max_tokens=2500,
        )
    )


def optional_reflect(bid, query):
    started = time.monotonic()
    try:
        return {
            "status": "ok",
            "elapsed_s": round(time.monotonic() - started, 3),
            "result": dump(
                client.reflect(
                    bid,
                    query,
                    budget="low",
                    include_facts=True,
                    max_tokens=600,
                )
            ),
        }
    except Exception as exc:
        return {
            "status": "finding",
            "elapsed_s": round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


bp = bank("preference")
retain(bp, fixtures["preference"], "pref-1")

bc = bank("correction")
retain(bc, fixtures["correction_before"], "corr-1")
retain(bc, fixtures["correction_after"], "corr-2")

bx = bank("conflict")
retain(bx, fixtures["conflict_a"], "conf-1")
retain(bx, fixtures["conflict_b"], "conf-2")

ba = bank("private-a")
bb = bank("private-b")
retain(ba, fixtures["private_a"], "private-a")
retain(bb, fixtures["private_b"], "private-b")

bf = bank("forget")
retain(bf, fixtures["forget"], "forget-doc")

# Persist every core result as soon as it exists. Optional higher-order reflection
# must never erase otherwise valid comparison evidence.
result["preference"] = recall(bp, "What communication preference was explicitly stated?")
save()

result["correction"] = recall(
    bc,
    "What is the current music lesson day and time, and what evidence changed?",
)
save()

result["conflict"] = recall(
    bx,
    "What pickup times were explicitly stated? Preserve unresolved conflict.",
)
save()

result["isolation_a_own"] = recall(ba, "MEMCMP_ALPHA_PRIVATE_70B8D4")
result["isolation_a_cross"] = recall(ba, "MEMCMP_BETA_PRIVATE_24E91A")
result["isolation_b_cross"] = recall(bb, "MEMCMP_ALPHA_PRIVATE_70B8D4")
save()

result["forget_before"] = recall(bf, "MEMCMP_FORGET_91C6E3")
save()

# The generated low-level Documents API is async-only and its aiohttp session is
# created by the sync Hindsight client's internal event-loop wrappers. Calling it
# through a fresh asyncio.run() therefore crosses loop ownership. Exercise the
# documented HTTP endpoint directly instead of testing an invalid client usage.
delete_url = (
    f"{base_url}/v1/default/banks/{urllib.parse.quote(bf, safe='')}"
    f"/documents/{urllib.parse.quote('forget-doc', safe='')}"
)
request = urllib.request.Request(delete_url, method="DELETE")
with urllib.request.urlopen(request, timeout=120) as response:
    result["forget_delete"] = json.loads(response.read().decode("utf-8"))
save()

time.sleep(1)
result["forget_after"] = recall(bf, "MEMCMP_FORGET_91C6E3")
result["meta"]["core_semantics_completed"] = True
save()

# Reflect is a useful Hindsight-specific capability benchmark, but it is not part
# of the common semantics gate. A prior qwen3.5:9b run timed out, so keep it opt-in.
if run_reflect:
    result["correction_reflect"] = optional_reflect(
        bc,
        "State the current music lesson time and explain the correction history without reversing it.",
    )
    if result["correction_reflect"]["status"] == "ok":
        result["conflict_reflect"] = optional_reflect(
            bx,
            "Are the pickup-time claims resolved or contradictory? Do not invent a correction.",
        )
    else:
        result["conflict_reflect"] = {
            "status": "skipped",
            "reason": "correction_reflect did not complete; avoid a second long local-model timeout",
        }
else:
    result["correction_reflect"] = {
        "status": "skipped",
        "reason": "optional benchmark disabled; prior local qwen3.5:9b reflect exceeded practical latency",
    }
    result["conflict_reflect"] = {
        "status": "skipped",
        "reason": "optional benchmark disabled",
    }
save()
