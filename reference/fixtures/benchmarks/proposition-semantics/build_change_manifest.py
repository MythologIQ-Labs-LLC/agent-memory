#!/usr/bin/env python3
"""Build the draft v1 -> draft v2 change manifest from the two annotation files (#594).

Reads only the frozen sample, the two draft annotation files, and their rubric
files. It imports nothing from Agent Memory and never runs the interpreter.
Every changed item must carry a ``v2_change_reason`` in draft v2, otherwise the
build fails.

    python3 build_change_manifest.py          # rewrite the manifest
    python3 build_change_manifest.py --check  # exit 1 if the committed manifest is stale
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE, V1, V2 = HERE / "sample-v1.json", HERE / "draft-annotations-v1.json", HERE / "draft-annotations-v2.json"
OUT = HERE / "draft-v1-to-v2-change-manifest.json"
STATUSES = ("known", "ambiguous", "unknown")
LABEL_FIELDS = (
    "status", "propositions", "principal", "cardinality", "temporal_aspect", "aspect_explicit",
    "change_marker", "coexistence_marker", "hedged", "self_authority_claim", "temporal_language_non_temporal",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _principal(item: dict):
    return None if item["principal"] is None else item["propositions"][item["principal"]]


def _ruling_class(item: dict) -> str:
    ruling = item.get("maintainer_ruling") or ""
    if ruling.startswith("CHANGE"):
        return "maintainer_ruling_change"
    if ruling.startswith("KEEP"):
        return "maintainer_ruling_keep_status"
    return "corpus_rereview"


def build() -> dict:
    sample = {i["item_id"]: i for i in json.loads(SAMPLE.read_text(encoding="utf-8"))["items"]}
    v1_doc, v2_doc = json.loads(V1.read_text(encoding="utf-8")), json.loads(V2.read_text(encoding="utf-8"))
    changes = []
    matrix = {old: Counter() for old in STATUSES}
    for old, new in zip(v1_doc["items"], v2_doc["items"]):
        assert old["item_id"] == new["item_id"]
        matrix[old["status"]][new["status"]] += 1
        fields = [f for f in LABEL_FIELDS if old[f] != new[f]]
        if not fields:
            continue
        if not new.get("v2_change_reason"):
            raise SystemExit(f"{new['item_id']} changed ({fields}) but has no v2_change_reason")
        source = sample[new["item_id"]]
        changes.append({
            "item_id": new["item_id"],
            "part": "random" if source["part"] == "R" else "stratified",
            "stratum": source["stratum"],
            "origin": source["origin"],
            "status_v1": old["status"], "status_v2": new["status"],
            "principal_v1": _principal(old), "principal_v2": _principal(new),
            "cardinality_v1": old["cardinality"], "cardinality_v2": new["cardinality"],
            "temporal_aspect_v1": old["temporal_aspect"], "temporal_aspect_v2": new["temporal_aspect"],
            "fields_changed": fields,
            "reason": new["v2_change_reason"],
            "ruling_class": _ruling_class(new),
        })

    def group(key) -> dict:
        grouped = defaultdict(list)
        for change in changes:
            grouped[key(change)].append(change["item_id"])
        return {k: {"count": len(v), "items": v} for k, v in sorted(grouped.items())}

    def transition(change) -> str:
        return f"{change['status_v1']}->{change['status_v2']}"

    by_part = {}
    for part in ("random", "stratified"):
        subset = [c for c in changes if c["part"] == part]
        by_part[part] = {
            "items_in_part": sum(1 for s in sample.values() if (s["part"] == "R") == (part == "random")),
            "items_changed": len(subset),
            "status_transitions": dict(sorted(Counter(transition(c) for c in subset).items())),
            "reasons": dict(sorted(Counter(c["reason"] for c in subset).items())),
        }
    by_stratum = {}
    for stratum in sorted({s["stratum"] for s in sample.values() if s["stratum"]}):
        subset = [c for c in changes if c["stratum"] == stratum]
        by_stratum[stratum] = {
            "items_in_stratum": sum(1 for s in sample.values() if s["stratum"] == stratum),
            "items_changed": len(subset),
            "status_transitions": dict(sorted(Counter(transition(c) for c in subset).items())),
            "items": [c["item_id"] for c in subset],
        }
    def counts(doc: dict, parts: tuple[str, ...]) -> dict:
        return {s: sum(1 for i in doc["items"] if i["status"] == s and sample[i["item_id"]]["part"] in parts) for s in STATUSES}

    status_counts = {
        name: {"all": counts(doc, ("R", "S")), "random": counts(doc, ("R",)), "stratified": counts(doc, ("S",))}
        for name, doc in (("v1", v1_doc), ("v2", v2_doc))
    }
    return {
        "manifest": "proposition-semantics draft v1 -> draft v2 change manifest",
        "status_labels": ["DRAFT", "MODEL-ASSISTED", "NOT ACCEPTED GOLD", "NOT SCORED"],
        "interpreter_output_consulted": False,
        "generated_by": "build_change_manifest.py",
        "v1": {"file": V1.name, "sha256": _sha(V1), "rubric": "annotation-rubric.md", "rubric_sha256": v1_doc["rubric_sha256"]},
        "v2": {"file": V2.name, "sha256": _sha(V2), "rubric": "annotation-rubric-v2.md", "rubric_sha256": v2_doc["rubric_sha256"]},
        "items_reviewed": len(v2_doc["items"]),
        "items_changed": len(changes),
        "items_unchanged": len(v2_doc["items"]) - len(changes),
        "status_counts": status_counts,
        "status_transition_matrix": {old: {new: matrix[old][new] for new in STATUSES} for old in STATUSES},
        "field_change_counts": {
            "status": sum(c["status_v1"] != c["status_v2"] for c in changes),
            "principal_proposition": sum(c["principal_v1"] != c["principal_v2"] for c in changes),
            "cardinality": sum(c["cardinality_v1"] != c["cardinality_v2"] for c in changes),
            "temporal_aspect": sum(c["temporal_aspect_v1"] != c["temporal_aspect_v2"] for c in changes),
        },
        "maintainer_rulings": {
            "total": sum(1 for i in v2_doc["items"] if i.get("maintainer_ruling")),
            "change": [i["item_id"] for i in v2_doc["items"] if (i.get("maintainer_ruling") or "").startswith("CHANGE")],
            "keep": [i["item_id"] for i in v2_doc["items"] if (i.get("maintainer_ruling") or "").startswith("KEEP")],
        },
        "by_status_transition": group(transition),
        "by_reason": group(lambda c: c["reason"]),
        "by_ruling_class": group(lambda c: c["ruling_class"]),
        "by_part": by_part,
        "by_stratum": by_stratum,
        "changes": changes,
    }


def render() -> str:
    return json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == text else 1)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.name}")
