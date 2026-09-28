"""#594: #550 write-time semantic activation per ingested LongMemEval_S memory, by profile.

Usage: PYTHONPATH=reference python semantic_activation.py SOURCE.json OUT.json

Counts every ingested memory (per plane, duplicates included, as the runner ingests
them) under the canonical profile (no declared temporal) and the source-anchored
profile (declared observed_at = session date). Calls exactly the function the adapter
calls on write (``interpret_write(fact_text, declared_temporal=declared)``). Only
aggregate counts are emitted; no text.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import run_longmemeval as lme
from agentmem_ref.runtime import proposition_semantics as ps

source, out_path = Path(sys.argv[1]), Path(sys.argv[2])
raw = source.read_bytes()
data = json.loads(raw)
cache: dict[tuple[str, str | None], dict] = {}


def interpret(text, observed):
    key = (text, observed)
    if key not in cache:
        declared = {"observed_at": observed} if observed else None
        cache[key] = ps.interpret_write(text, declared_temporal=declared)
    return cache[key]


out = {"input_sha256": hashlib.sha256(raw).hexdigest(), "interpreter": {"ref": ps.INTERPRETER_REF, "version": ps.INTERPRETER_VERSION}, "planes": {}}
for plane in ("session", "turn"):
    section = {}
    for profile, anchored in (("canonical", False), ("source_anchored", True)):
        counts = Counter()
        validity = Counter()
        for row in data:
            items, _ = lme.corpus(row, plane)
            for item in items:
                observed = lme._iso_date(item["date"]) if anchored else None
                result = interpret(item["text"], observed)
                counts["memories_ingested"] += 1
                counts["memories_with_observed_at"] += observed is not None
                status = result["proposition"]["status"]
                counts[f"proposition_{status}"] += 1
                sv = (result.get("self_validity") or {}).get("status", "none")
                validity[sv] += 1
                resolved = sv == "resolved"
                aspect = bool((result.get("markers") or {}).get("aspect"))
                counts["interpreted_self_validity_resolved"] += resolved
                counts["interpreted_self_validity_expression_present"] += sv != "none"
                counts["temporal_aspect_only"] += aspect and not resolved
                counts["temporal_aspect_any"] += aspect
                counts["cardinality_" + result["cardinality"]["class"]] += 1
        section[profile] = {**dict(sorted(counts.items())), "self_validity_status": dict(sorted(validity.items()))}
    out["planes"][plane] = section
out_path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
print(json.dumps(out["planes"], indent=1))
