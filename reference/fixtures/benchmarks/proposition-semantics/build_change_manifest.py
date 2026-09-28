#!/usr/bin/env python3
"""Build the draft change manifests (v1 -> v2, v2 -> v3) from the annotation files (#594).

Reads only the frozen sample and the draft annotation files. It imports nothing
from Agent Memory and never runs the interpreter. Every changed item must carry
the newer draft's ``vN_change_reason``, otherwise the build fails.

    python3 build_change_manifest.py          # rewrite the manifests
    python3 build_change_manifest.py --check  # exit 1 if a committed manifest is stale
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "sample-v1.json"
PAIRS = {
    "draft-v1-to-v2-change-manifest.json": ("v1", "v2"),
    "draft-v2-to-v3-change-manifest.json": ("v2", "v3"),
    "draft-v3-to-v4-change-manifest.json": ("v3", "v4"),
}
# The maintainer review whose rulings a version applies; its items get their own ruling class.
REVIEW_FIELDS = {"v3": ("maintainer_review_2", "maintainer_second_review"), "v4": ("maintainer_review_3", "maintainer_third_review")}
RUBRICS = {"v1": "annotation-rubric.md", "v2": "annotation-rubric-v2.md", "v3": "annotation-rubric-v3.md", "v4": "annotation-rubric-v4.md"}
STATUSES = ("known", "ambiguous", "unknown")
LABEL_FIELDS = (
    "status", "propositions", "principal", "cardinality", "temporal_aspect", "aspect_explicit",
    "change_marker", "coexistence_marker", "hedged", "self_authority_claim", "temporal_language_non_temporal",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _principal(item: dict):
    return None if item["principal"] is None else item["propositions"][item["principal"]]


COMPARED = {
    "status": lambda item: item["status"],
    "principal": lambda item: _principal(item),
    "cardinality": lambda item: item["cardinality"],
    "temporal_aspect": lambda item: item["temporal_aspect"],
}


def _ruling_class(item: dict, reason: str, version: str) -> str:
    field, name = REVIEW_FIELDS.get(version, (None, None))
    if field and item.get(field):
        return name
    if reason == "maintainer_boundary_ruling":
        return "maintainer_ruling_change"
    if item.get("maintainer_ruling"):
        return "corpus_rereview_on_ruled_item"
    return "corpus_rereview"


def build(old_version: str, new_version: str) -> dict:
    sample = {i["item_id"]: i for i in json.loads(SAMPLE.read_text(encoding="utf-8"))["items"]}
    V1, V2 = HERE / f"draft-annotations-{old_version}.json", HERE / f"draft-annotations-{new_version}.json"
    v1_doc, v2_doc = json.loads(V1.read_text(encoding="utf-8")), json.loads(V2.read_text(encoding="utf-8"))
    reason_field = f"{new_version}_change_reason"
    changes = []
    matrix = {old: Counter() for old in STATUSES}
    for old, new in zip(v1_doc["items"], v2_doc["items"]):
        assert old["item_id"] == new["item_id"]
        matrix[old["status"]][new["status"]] += 1
        fields = [f for f in LABEL_FIELDS if old[f] != new[f]]
        if not fields:
            continue
        if not new.get(reason_field):
            raise SystemExit(f"{new['item_id']} changed ({fields}) but has no {reason_field}")
        source = sample[new["item_id"]]
        changes.append({
            "item_id": new["item_id"],
            "part": "random" if source["part"] == "R" else "stratified",
            "stratum": source["stratum"],
            "origin": source["origin"],
            **{f"{field}_{old_version}": value(old) for field, value in COMPARED.items()},
            **{f"{field}_{new_version}": value(new) for field, value in COMPARED.items()},
            "fields_changed": fields,
            "reason": new[reason_field],
            "notes": new["notes"],
            "ruling_class": _ruling_class(new, new[reason_field], new_version),
        })

    def group(key) -> dict:
        grouped = defaultdict(list)
        for change in changes:
            grouped[key(change)].append(change["item_id"])
        return {k: {"count": len(v), "items": v} for k, v in sorted(grouped.items())}

    def transition(change) -> str:
        return f"{change[f'status_{old_version}']}->{change[f'status_{new_version}']}"

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
        for name, doc in ((old_version, v1_doc), (new_version, v2_doc))
    }
    return {
        "manifest": f"proposition-semantics draft {old_version} -> draft {new_version} change manifest",
        "status_labels": ["DRAFT", "MODEL-ASSISTED", "NOT ACCEPTED GOLD", "NOT SCORED"],
        "interpreter_output_consulted": False,
        "generated_by": "build_change_manifest.py",
        "old": {"version": old_version, "file": V1.name, "sha256": _sha(V1), "rubric": RUBRICS[old_version], "rubric_sha256": v1_doc["rubric_sha256"]},
        "new": {"version": new_version, "file": V2.name, "sha256": _sha(V2), "rubric": RUBRICS[new_version], "rubric_sha256": v2_doc["rubric_sha256"]},
        "items_reviewed": len(v2_doc["items"]),
        "items_changed": len(changes),
        "items_unchanged": len(v2_doc["items"]) - len(changes),
        "status_counts": status_counts,
        "status_transition_matrix": {old: {new: matrix[old][new] for new in STATUSES} for old in STATUSES},
        "field_change_counts": {
            ("principal_proposition" if field == "principal" else field):
                sum(c[f"{field}_{old_version}"] != c[f"{field}_{new_version}"] for c in changes)
            for field in COMPARED
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


def rereview_of_earlier_changes(manifest: dict, earlier: dict) -> dict:
    """For v2 -> v3: the outcome of re-reviewing every v1 -> v2 change."""

    revised = {c["item_id"]: c["reason"] for c in manifest["changes"]}
    outcomes = {item["item_id"]: ("revised_in_v3: " + revised[item["item_id"]]) if item["item_id"] in revised else "confirmed"
                for item in earlier["changes"]}
    return {"items": len(outcomes), "confirmed": sum(v == "confirmed" for v in outcomes.values()),
            "revised": sum(v != "confirmed" for v in outcomes.values()), "outcomes": dict(sorted(outcomes.items()))}


def render(name: str) -> str:
    manifest = build(*PAIRS[name])
    if PAIRS[name] == ("v2", "v3"):
        manifest["rereview_of_v1_to_v2_changes"] = rereview_of_earlier_changes(manifest, build("v1", "v2"))
    return json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    stale = []
    for name in PAIRS:
        text, out = render(name), HERE / name
        if "--check" in sys.argv:
            stale += [] if out.exists() and out.read_text(encoding="utf-8") == text else [name]
        else:
            out.write_text(text, encoding="utf-8")
            print(f"wrote {name}")
    sys.exit(1 if stale else 0)
