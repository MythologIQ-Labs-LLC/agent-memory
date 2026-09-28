"""#550: how much of LongMemEval_S's natural user text does the typed write-time carrier cover?

Usage: PYTHONPATH=reference python lme_carrier_coverage.py <repo_root> <longmemeval_s_cleaned.json> <out.json>

Interprets every unique user turn (the turn-plane corpus of the bound upstream
replication) with ``interpret_write`` and no anchor (as the default replay writes them),
and counts proposition status, cardinality, markers, and whether each #583 cue that
occurs in a turn is carried by the typed ``aspect`` marker. No text is emitted.
"""
import hashlib, json, sys
from collections import Counter
from pathlib import Path

root, data_path, out_path = sys.argv[1:4]
sys.path.insert(0, str(Path(root) / "reference"))
import run_longmemeval as lme  # noqa: E402
from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402

raw = Path(data_path).read_bytes()
status, card, markers, aspect, carried, total = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
seen = set()
for row in json.loads(raw):
    items, _ = lme.corpus(row, "turn")
    for item in items:
        text = item["text"]
        if text in seen:
            continue
        seen.add(text)
        out = ps.interpret_write(text)
        status[out["proposition"]["status"]] += 1
        card[out["cardinality"]["class"]] += 1
        found = out.get("markers", {})
        for name, value in found.items():
            if value:
                markers[name] += 1
        for name in found.get("aspect", {}):
            aspect[name] += 1
        normalized = ps._norm(text)
        for cue, kind in (("currently", "present"), ("planning to", "prospective"), ("going to", "prospective")):
            if ps._contains(normalized, cue):
                total[cue] += 1
                carried[cue] += cue in found.get("aspect", {}).get(kind, [])
Path(out_path).write_text(json.dumps({
    "input_sha256": hashlib.sha256(raw).hexdigest(), "interpreter": {"ref": ps.INTERPRETER_REF, "version": ps.INTERPRETER_VERSION},
    "unique_user_turns": len(seen), "proposition_status": dict(sorted(status.items())), "cardinality": dict(sorted(card.items())),
    "turns_with_marker": dict(sorted(markers.items())), "turns_with_aspect": dict(sorted(aspect.items())),
    "cues_583_carried_by_typed_aspect": {cue: {"carried": carried[cue], "occurrences": total[cue]} for cue in sorted(total)},
}, indent=1, sort_keys=True) + "\n")
