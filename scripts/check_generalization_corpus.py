#!/usr/bin/env python3
"""Mechanical checks K1-K8 for the #732 generalization corpus (plan-732-generalization-gate G3).

This script never reads the runtime and never runs a case. It checks the author's
``corpus.json`` and, optionally, ``variants.json`` against the frozen schema and structural
rules. It then emits one rejection per failing record, as compact JSON ``[{id, file, rule}]``.
That JSON is the ``{REJECTIONS}`` value interpolated into the frozen ``replace.txt``. A record
is reported once, under the first rule it fails, in the order K1..K8.

The rules:

* ``K1_fields``: the exact field set and types, ids unique across both files, ``target_reference``
  unique within a record, indices in range, and no non-null ``source_ref`` beginning with
  ``actor:``.
* ``K2_expected``: P and R families expect ``engage``, N families expect ``refrain``. A variant's
  ``expected`` matches its kind.
* ``K3_order``: ``older_write < newer_write``.
* ``K4_recall_as_wrote``: ``recall_as`` is the ``(handle, scope)`` of at least one write.
* ``K5_structure_<family>``: base cases only. Sources are compared as effective sources, where
  null means ``actor:<handle>``; N9 compares declared sources instead.
* ``K6_variant_<type>``: a variant is compared with its base. The rule also covers
  ``n/a`` on a must-change type, a missing (base, type) pair (id ``<base>:<type>``) and a
  duplicate pair (``K6_variant_set_*``).
* ``K7_g3b_overlap``: any write text or query whose similarity with any of the 15 MESA
  ``CONFLICT_TEMPLATES`` texts is at least 0.5. The templates come from
  ``reference/run_semantic_route_ordering_report.py`` at blob ``745f789c``.
* ``K8_holdout_overlap``: holdouts only (``--prior``). Any text with similarity of at least 0.5
  against any text of a prior corpus fails.

Similarity: text is lower-cased and tokenised with ``[a-z0-9]+``. If both texts have at least 3
tokens, similarity is the Jaccard of their token trigrams. Otherwise it is the Jaccard of their
token sets. Two empty sets score 0.

The script has ``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SOURCE = ROOT / "reference" / "run_semantic_route_ordering_report.py"
TEMPLATE_BLOB_PREFIX = "745f789c"
THRESHOLD = 0.5

P_FAMILIES = [f"P{i}" for i in range(1, 14)]
R_FAMILIES = [f"R{i}" for i in range(1, 8)]
N_FAMILIES = [f"N{i}" for i in range(1, 14)]
FAMILIES = P_FAMILIES + R_FAMILIES + N_FAMILIES
EXACT_SIZE = {**{f: 12 for f in P_FAMILIES}, **{f: 8 for f in R_FAMILIES + N_FAMILIES}}
INVARIANCE = ["punctuation", "apostrophe", "adverb_placement", "subject_wording", "value_case", "unit_spelling"]
MUST_CHANGE = ["hedge", "attribution", "conditional", "coexistent", "change_source_ref", "change_actor", "change_scope", "dispute"]
TEXT_ONLY = {"hedge", "attribution", "conditional", "coexistent"}

CASE_FIELDS = {"case_id", "family", "expected", "writes", "older_write", "newer_write", "actions", "recall_as", "query", "rationale"}
VARIANT_FIELDS = {"variant_id", "base_case_id", "variant_type", "kind", "expected", "writes", "older_write", "newer_write", "actions", "recall_as", "query", "rationale"}
NA_FIELDS = {"variant_id", "base_case_id", "variant_type", "kind", "na_reason"}
WRITE_FIELDS = {"handle", "scope", "target_reference", "text", "source_ref"}
BODY_FIELDS = ["writes", "older_write", "newer_write", "actions", "recall_as", "query"]
TOKEN = re.compile(r"[a-z0-9]+")


class Reject(Exception):
    def __init__(self, rule: str):
        super().__init__(rule)
        self.rule = rule


# --- similarity -------------------------------------------------------------------------------

def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if len(ta) >= 3 and len(tb) >= 3:
        sa = {tuple(ta[i:i + 3]) for i in range(len(ta) - 2)}
        sb = {tuple(tb[i:i + 3]) for i in range(len(tb) - 2)}
    else:
        sa, sb = set(ta), set(tb)
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def template_texts() -> list[str]:
    blob = subprocess.run(
        ["git", "hash-object", str(TEMPLATE_SOURCE)], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    if not blob.startswith(TEMPLATE_BLOB_PREFIX):
        raise SystemExit(f"template source blob {blob} is not the frozen {TEMPLATE_BLOB_PREFIX}")
    tree = ast.parse(TEMPLATE_SOURCE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "CONFLICT_TEMPLATES" for t in node.targets):
            rows = ast.literal_eval(node.value)
            break
    else:
        raise SystemExit("CONFLICT_TEMPLATES not found")
    texts = []
    for _slot, old, new, query in rows:
        texts += [old.replace("{old}", ""), new.replace("{new}", ""), query]
    if len(texts) != 15:
        raise SystemExit(f"expected 15 template texts, found {len(texts)}")
    return texts


def record_texts(record: dict) -> list[str]:
    return [w["text"] for w in record.get("writes", [])] + [record.get("query", "")]


# --- K1 -----------------------------------------------------------------------------------------

def _nonempty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _index(value, n: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < n


def check_body(record: dict) -> None:
    writes = record["writes"]
    if not isinstance(writes, list) or len(writes) < 2:
        raise Reject("K1_fields")
    refs = []
    for write in writes:
        if not isinstance(write, dict) or set(write) != WRITE_FIELDS:
            raise Reject("K1_fields")
        if write["handle"] not in ("A", "B") or write["scope"] not in ("S1", "S2"):
            raise Reject("K1_fields")
        if not _nonempty_str(write["target_reference"]) or not _nonempty_str(write["text"]):
            raise Reject("K1_fields")
        source = write["source_ref"]
        if source is not None and (not _nonempty_str(source) or source.startswith("actor:")):
            raise Reject("K1_fields")
        refs.append(write["target_reference"])
    if len(set(refs)) != len(refs):
        raise Reject("K1_fields")
    n = len(writes)
    if not _index(record["older_write"], n) or not _index(record["newer_write"], n):
        raise Reject("K1_fields")
    if record["older_write"] == record["newer_write"]:
        raise Reject("K1_fields")
    actions = record["actions"]
    if not isinstance(actions, list):
        raise Reject("K1_fields")
    for action in actions:
        if not isinstance(action, dict) or set(action) != {"action", "write"}:
            raise Reject("K1_fields")
        if action["action"] not in ("dispute", "forget") or not _index(action["write"], n):
            raise Reject("K1_fields")
    recall_as = record["recall_as"]
    if not isinstance(recall_as, dict) or set(recall_as) != {"handle", "scope"}:
        raise Reject("K1_fields")
    if recall_as["handle"] not in ("A", "B") or recall_as["scope"] not in ("S1", "S2"):
        raise Reject("K1_fields")
    if not _nonempty_str(record["query"]) or not _nonempty_str(record["rationale"]):
        raise Reject("K1_fields")


def check_order_and_recall(record: dict) -> None:
    if not record["older_write"] < record["newer_write"]:
        raise Reject("K3_order")
    wrote = {(w["handle"], w["scope"]) for w in record["writes"]}
    if (record["recall_as"]["handle"], record["recall_as"]["scope"]) not in wrote:
        raise Reject("K4_recall_as_wrote")


# --- K5 -----------------------------------------------------------------------------------------

def effective_source(write: dict) -> str:
    return write["source_ref"] if write["source_ref"] is not None else f"actor:{write['handle']}"


def check_structure(case: dict) -> None:
    family = case["family"]
    old, new = case["writes"][case["older_write"]], case["writes"][case["newer_write"]]
    actions = case["actions"]
    same_handle = old["handle"] == new["handle"]
    same_scope = old["scope"] == new["scope"]
    same_source = effective_source(old) == effective_source(new)
    recall_is_old = case["recall_as"] == {"handle": old["handle"], "scope": old["scope"]}
    rule = f"K5_structure_{family}"
    if family in ("N7",):
        ok = same_scope and old["source_ref"] is not None and new["source_ref"] is not None and not same_source and not actions
    elif family == "N8":
        ok = same_handle and same_scope and not same_source and not actions
    elif family == "N9":
        ok = not same_handle and same_scope and old["source_ref"] == new["source_ref"] and not actions
    elif family == "N10":
        ok = not same_scope and same_handle and same_source and not actions
    elif family == "N13":
        ok = same_handle and same_scope and same_source and any(a["write"] == case["newer_write"] for a in actions)
    else:
        ok = same_handle and same_scope and same_source and not actions and recall_is_old
    if not ok:
        raise Reject(rule)


# --- K6 -----------------------------------------------------------------------------------------

def _body(record: dict) -> dict:
    return {key: copy.deepcopy(record[key]) for key in BODY_FIELDS}


def check_variant(variant: dict, base: dict) -> None:
    vtype = variant["variant_type"]
    rule = f"K6_variant_{vtype}"
    vb, bb = _body(variant), _body(base)
    if vtype in INVARIANCE:
        if len(vb["writes"]) != len(bb["writes"]):
            raise Reject(rule)
        stripped_v = copy.deepcopy(vb)
        stripped_b = copy.deepcopy(bb)
        for record in (stripped_v, stripped_b):
            record["query"] = ""
            for write in record["writes"]:
                write["text"] = ""
        if stripped_v != stripped_b:
            raise Reject(rule)
        if all(v["text"] == b["text"] for v, b in zip(vb["writes"], bb["writes"])):
            raise Reject(rule)
        return
    if vb["older_write"] != bb["older_write"] or vb["newer_write"] != bb["newer_write"]:
        raise Reject(rule)
    if len(vb["writes"]) != len(bb["writes"]):
        raise Reject(rule)
    newer, older = bb["newer_write"], bb["older_write"]
    restored = copy.deepcopy(vb)
    vnew = vb["writes"][newer]
    if vtype in TEXT_ONLY:
        if vnew["text"] == bb["writes"][newer]["text"]:
            raise Reject(rule)
        restored["writes"][newer]["text"] = bb["writes"][newer]["text"]
    elif vtype == "change_source_ref":
        if vnew["source_ref"] == vb["writes"][older]["source_ref"]:
            raise Reject(rule)
        restored["writes"][newer]["source_ref"] = bb["writes"][newer]["source_ref"]
    elif vtype == "change_actor":
        if vnew["handle"] == vb["writes"][older]["handle"]:
            raise Reject(rule)
        restored["writes"][newer]["handle"] = bb["writes"][newer]["handle"]
    elif vtype == "change_scope":
        if vnew["scope"] == vb["writes"][older]["scope"]:
            raise Reject(rule)
        restored["writes"][newer]["scope"] = bb["writes"][newer]["scope"]
    elif vtype == "dispute":
        if vb["actions"] != bb["actions"] + [{"action": "dispute", "write": newer}]:
            raise Reject(rule)
        restored["actions"] = bb["actions"]
    if restored != bb:
        raise Reject(rule)


# --- driver -------------------------------------------------------------------------------------

def overlap_rule(record: dict, references: list[str], rule: str) -> None:
    for text in record_texts(record):
        for reference in references:
            if similarity(text, reference) >= THRESHOLD:
                raise Reject(rule)


def check(corpus: list, variants: list | None, selection: list | None, prior_texts: list[str]) -> dict:
    templates = template_texts()
    rejections: list[dict] = []
    seen_ids: set = set()
    valid_cases: dict = {}

    if not isinstance(corpus, list):
        raise SystemExit("corpus.json must be a JSON array")
    for record in corpus:
        rid = record.get("case_id") if isinstance(record, dict) else None
        try:
            if not isinstance(record, dict) or set(record) != CASE_FIELDS or not _nonempty_str(rid):
                raise Reject("K1_fields")
            if rid in seen_ids or record["family"] not in FAMILIES:
                raise Reject("K1_fields")
            check_body(record)
            if record["expected"] != ("refrain" if record["family"].startswith("N") else "engage"):
                raise Reject("K2_expected")
            check_order_and_recall(record)
            check_structure(record)
            overlap_rule(record, templates, "K7_g3b_overlap")
            if prior_texts:
                overlap_rule(record, prior_texts, "K8_holdout_overlap")
            valid_cases[rid] = record
        except Reject as exc:
            rejections.append({"id": rid if isinstance(rid, str) else "<missing>", "file": "corpus.json", "rule": exc.rule})
        if isinstance(rid, str):
            seen_ids.add(rid)

    family_counts = Counter(case["family"] for case in valid_cases.values())
    report = {
        "family_valid_counts": {f: family_counts.get(f, 0) for f in FAMILIES},
        "family_short": {f: EXACT_SIZE[f] - family_counts.get(f, 0) for f in FAMILIES if family_counts.get(f, 0) < EXACT_SIZE[f]},
        "family_over": {f: family_counts[f] - EXACT_SIZE[f] for f in FAMILIES if family_counts.get(f, 0) > EXACT_SIZE[f]},
    }

    if variants is not None:
        selected = set(selection or [])
        pairs: set = set()
        for record in variants:
            rid = record.get("variant_id") if isinstance(record, dict) else None
            try:
                if not isinstance(record, dict) or not _nonempty_str(rid) or rid in seen_ids:
                    raise Reject("K1_fields")
                vtype, kind = record.get("variant_type"), record.get("kind")
                if vtype not in INVARIANCE + MUST_CHANGE or record.get("base_case_id") not in selected:
                    raise Reject("K1_fields")
                if kind != ("invariance" if vtype in INVARIANCE else "must_change"):
                    raise Reject("K1_fields")
                pair = (record["base_case_id"], vtype)
                if pair in pairs:
                    raise Reject("K6_variant_set_duplicate")
                if set(record) == NA_FIELDS:
                    if vtype not in INVARIANCE:
                        raise Reject(f"K6_variant_{vtype}")
                    if not _nonempty_str(record["na_reason"]):
                        raise Reject("K1_fields")
                    pairs.add(pair)
                    continue
                if set(record) != VARIANT_FIELDS:
                    raise Reject("K1_fields")
                check_body(record)
                if record["expected"] != ("same_as_base" if kind == "invariance" else "refrain"):
                    raise Reject("K2_expected")
                check_order_and_recall(record)
                base = valid_cases.get(record["base_case_id"])
                if base is None:
                    raise Reject("K1_fields")
                check_variant(record, base)
                overlap_rule(record, templates, "K7_g3b_overlap")
                if prior_texts:
                    overlap_rule(record, prior_texts, "K8_holdout_overlap")
                pairs.add(pair)
            except Reject as exc:
                rejections.append({"id": rid if isinstance(rid, str) else "<missing>", "file": "variants.json", "rule": exc.rule})
            if isinstance(rid, str):
                seen_ids.add(rid)
        for base_id in sorted(selected):
            for vtype in INVARIANCE + MUST_CHANGE:
                if (base_id, vtype) not in pairs and not any(
                    r["file"] == "variants.json" and r["id"] in _ids_for(variants, base_id, vtype) for r in rejections
                ):
                    rejections.append({"id": f"{base_id}:{vtype}", "file": "variants.json", "rule": "K6_variant_set_complete"})

    rejections.sort(key=lambda r: (r["file"], r["id"], r["rule"]))
    report.update({
        "rejections": rejections,
        "valid_case_ids": sorted(valid_cases),
        "template_blob_prefix": TEMPLATE_BLOB_PREFIX,
        "authority_effect": "none",
    })
    return report


def _ids_for(variants: list, base_id: str, vtype: str) -> set:
    return {
        r.get("variant_id")
        for r in variants
        if isinstance(r, dict) and r.get("base_case_id") == base_id and r.get("variant_type") == vtype
    }


def compact(value) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--variants", type=Path)
    parser.add_argument("--selection", type=Path, help="compact JSON list from select_metamorphic_bases.py")
    parser.add_argument("--prior", type=Path, action="append", default=[], help="prior corpus or variants file (holdouts)")
    parser.add_argument("--report", type=Path, help="write the full report here")
    parser.add_argument("--rejections", type=Path, help="write the compact {REJECTIONS} JSON here")
    args = parser.parse_args(argv)

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    variants = json.loads(args.variants.read_text(encoding="utf-8")) if args.variants else None
    selection = json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else None
    prior_texts: list[str] = []
    for path in args.prior:
        for record in json.loads(path.read_text(encoding="utf-8")):
            if isinstance(record, dict) and "writes" in record:
                prior_texts += record_texts(record)
    report = check(corpus, variants, selection, prior_texts)
    report["inputs_sha256"] = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [args.corpus, args.variants, args.selection, *args.prior]
        if path is not None
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.rejections:
        args.rejections.write_text(compact(report["rejections"]), encoding="utf-8")
    sys.stdout.write(json.dumps({k: report[k] for k in ("family_short", "family_over")}, sort_keys=True) + "\n")
    sys.stdout.write(f"rejections: {len(report['rejections'])}\n")
    return 0 if not report["rejections"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
