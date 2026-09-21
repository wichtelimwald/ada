#!/usr/bin/env python3
import asyncio
import json
import sys
import time
from pathlib import Path

from hindsight_client import Hindsight

base_url, fixture_path, out_path = sys.argv[1:4]
fixtures = json.loads(Path(fixture_path).read_text())
out = Path(out_path)
out.mkdir(parents=True, exist_ok=True)
client = Hindsight(base_url=base_url, timeout=600)

for _ in range(90):
    try:
        client.get_version()
        break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError("Hindsight API did not become ready")

mission = fixtures["instructions"] + " Keep source evidence inspectable. Do not turn memory into authorization."


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
    response = client.recall(
        bid,
        query,
        types=["world", "experience", "observation"],
        include_source_facts=True,
        prefer_observations=True,
        max_tokens=2500,
    )
    return response.model_dump(mode="json") if hasattr(response, "model_dump") else str(response)


def reflect(bid, query):
    response = client.reflect(bid, query, budget="low", include_facts=True, max_tokens=1200)
    return response.model_dump(mode="json") if hasattr(response, "model_dump") else str(response)


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

result = {
    "preference": recall(bp, "What communication preference was explicitly stated?"),
    "correction": recall(bc, "What is the current music lesson day and time, and what evidence changed?"),
    "correction_reflect": reflect(bc, "State the current music lesson time and explain the correction history without reversing it."),
    "conflict": recall(bx, "What pickup times were explicitly stated? Preserve unresolved conflict."),
    "conflict_reflect": reflect(bx, "Are the pickup-time claims resolved or contradictory? Do not invent a correction."),
    "isolation_a_own": recall(ba, "MEMCMP_ALPHA_PRIVATE_70B8D4"),
    "isolation_a_cross": recall(ba, "MEMCMP_BETA_PRIVATE_24E91A"),
    "isolation_b_cross": recall(bb, "MEMCMP_ALPHA_PRIVATE_70B8D4"),
    "forget_before": recall(bf, "MEMCMP_FORGET_91C6E3"),
}

asyncio.run(client.documents.delete_document(bf, "forget-doc"))
time.sleep(1)
result["forget_after"] = recall(bf, "MEMCMP_FORGET_91C6E3")

(out / "semantic.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
