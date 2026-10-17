"""Classifies admitted memories that the fused top-``budget`` holds but selection withheld (#819 C9 diagnosis).

W1: positive topical relevance below the floor (``below_relative_floor``).
W2: no topical term match (``no_informative_term_match``).
For each, its role (must / may / other) and its cosine relative to the returned primary evidence.

    python analyze_withheld.py diag/C8sem-rs-*.json
"""
import json
import sys
from collections import Counter

PRIMARY = {"exact_identity", "non_lexical_route_evidence", "content_relevance"}
total = Counter()
for path in sys.argv[1:]:
    data = json.load(open(path))
    c = Counter()
    for row in data["rows"]:
        top = row["top_budget"]
        anchor = [t["cosine"] for t in top.values() if t["stage"] == "returned" and t["basis"] in PRIMARY and t["cosine"] is not None]
        lo = min(anchor) if anchor else None
        for ref, t in top.items():
            if t["stage"] != "withheld":
                continue
            cls = {"below_relative_floor": "W1", "no_informative_term_match": "W2"}.get(t["basis"], str(t["basis"]))
            role = "must" if t["role"] == "must" else "may" if t["role"] == "may" else "other"
            c[(cls, role)] += 1
            if lo is not None and t["cosine"] is not None and t["cosine"] >= lo:
                c[(cls, role, ">=anchor_min")] += 1
            if not anchor:
                c[(cls, role, "no_anchor")] += 1
    print(path, dict(sorted(c.items())))
    total.update(c)
print("TOTAL", dict(sorted(total.items())))
