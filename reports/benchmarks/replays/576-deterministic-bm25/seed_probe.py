"""#576 cross-process probe: run once per PYTHONHASHSEED and emit BM25 evidence as JSON.

Usage: PYTHONHASHSEED=<n> python seed_probe.py
Emits the pure ``admitted_set_bm25`` scores (float.hex, bit-exact), the order they
induce, and an end-to-end governed recall over the same texts (admitted/refused
sets, order, per-candidate ``lexical_relevance_score`` and ``ordered_before_next_by``).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import ranking_policy  # noqa: E402

# Near-tie fixture: m0, m3 and m5 are mathematically tied (each holds one occurrence of
# three query terms whose document frequencies are 4, 4 and 4-of-6, at the same length),
# so their float sums differ only by accumulation order. Under the pre-fix set order,
# PYTHONHASHSEED 0, 1 and 2 each produce a different ranking of this fixture.
QUERY = "alpha bravo charlie delta echo"
TEXTS = {
    "m0": "delta hotel echo charlie",
    "m1": "foxtrot golf delta alpha echo alpha foxtrot",
    "m2": "hotel delta foxtrot hotel golf charlie",
    "m3": "delta echo foxtrot alpha",
    "m4": "echo alpha",
    "m5": "echo delta hotel charlie",
}


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def pure() -> dict:
    scores = ranking_policy.admitted_set_bm25(QUERY, TEXTS)
    order = sorted(scores, key=lambda ref: (-scores[ref], ref))
    return {"scores_hex": {ref: score.hex() for ref, score in sorted(scores.items())},
            "scores_repr": {ref: repr(score) for ref, score in sorted(scores.items())},
            "order_by_score_then_ref": order}


def governed() -> dict:
    with tempfile.TemporaryDirectory() as root:
        memory = AgentMemory.open(root, tenant="tenant:576", actor_id="agent:576", scope="project:576", purpose="576 probe")
        refs = {}
        for key, text in TEXTS.items():
            result = memory.remember(f"memory:{key}", text)
            refs[result["fact_uuid"]] = key
        # Refusal path: a fully matching memory that is then forgotten stays a candidate
        # and must be refused. Refused candidates contribute no BM25 statistics.
        forgotten = memory.remember("memory:forgotten", QUERY + " forgotten")
        refs[forgotten["fact_uuid"]] = "forgotten"
        memory.forget("memory:forgotten")
        recalled = memory.recall(QUERY)
        memory.close()
    evidence = {refs.get(uuid, uuid): {
        "lexical_relevance_score": repr(adm.get("ranking_evidence", {}).get("lexical_relevance_score")),
        "ordered_before_next_by": adm.get("ranking_evidence", {}).get("ordered_before_next_by"),
        "outcome": adm["outcome"],
        "reason_code": adm["reason_code"],
    } for uuid, adm in recalled["admissions"].items()}
    admitted = set(recalled["admitted"])
    return {"admitted_order": [refs.get(u, u) for u in recalled["admitted"]],
            "candidates": sorted(refs.get(u, u) for u in recalled["candidates"]),
            "refused": sorted(refs.get(u, u) for u in recalled["candidates"] if u not in admitted),
            "ranking_evidence": dict(sorted(evidence.items()))}


if __name__ == "__main__":
    out = {"pythonhashseed": os.environ.get("PYTHONHASHSEED"),
           "set_iteration_order": list(set(ranking_policy.relevance_tokens(QUERY))),
           "pure": pure(), "governed": governed()}
    out["pure_digest"] = _digest(out["pure"])
    out["governed_digest"] = _digest(out["governed"])
    print(json.dumps(out, sort_keys=True))
