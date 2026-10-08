#!/usr/bin/env python3
"""#732 oracle-ceiling diagnostic: downstream currentness with perfect write-time typed evidence.

This is a **diagnostic**, not a score and not acceptance evidence. It answers one question the
frozen measurement (measurement-v1, 0/212) cannot: if write-time interpretation were perfect,
would the rest of the pipeline engage on legitimate changes and refrain on the controls? It
separates the write-interpretation stage from candidate generation, typed relation, the guards
(G1-G13), admission (S1/S2) and ranking (S6).

It never emits a G5 verdict: the measurement corpus is spent, and any successor mechanism must
be judged on a fresh holdout, never on this corpus.

Method. Every case and variant of the frozen measurement corpus runs through the unchanged
``run_currentness_generalization.run_record`` with an oracle ``PropositionExtractor`` attached to
every write handle through the public ``AgentMemory.open(..., proposition_extractor=...)``. The
oracle never reads the write text. Its typed record is derived only from corpus *metadata*
(family, variant type, write role), using placeholder subject/attribute/value tokens that share
one typed slot per case. It does use the corpus's role indices (``older_write``/``newer_write``)
and family/variant labels, and keys its answers by exact write text. Because every record shares
one placeholder slot, a ``typed_slot`` relation can form even when candidate generation missed
the older fact; those cases are reported separately (``candidate_generation``). The link to the older fact is returned only when the older fact is in
the candidates the runtime itself sent, so candidate generation is measured, not assumed.

Two oracle modes:

* ``gold``: the flag a correct interpreter would set for each negative family / must-change
  type (for example N4 and ``hedge`` -> ``hedged``). Structural controls (N7-N10, N13 and the
  ``change_*``/``dispute`` variants) receive a clean ``change`` record: their text is a clean
  change, and only actor/source/scope/lifecycle guards may refuse them.
* ``flag_blind``: every newer write receives a clean ``change`` record, as a worst-case
  extractor that misses every hedge, quote, sarcasm or condition. It measures which controls are
  protected only by extractor flags (no defense in depth) versus by structural guards.
* ``slot_drift``: ``gold`` labels and a correct link to the older fact, but the newer write names
  the same subject and attribute with different, equivalent wording (``the oracle subject`` /
  ``current oracle attribute``). A real extractor sees candidate *texts*, never their typed
  records, so independently chosen noun phrases can differ. This measures whether proposition
  identity survives that drift (R3 ``link_confirmed`` requires an identical typed slot).

Nothing under ``reference/agentmem_ref`` imports this file. It changes no runtime behaviour, uses
no credential and sends nothing off the process (the oracle is local; ``egress_policy`` is
irrelevant but required by the protocol). ``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

import run_currentness_generalization as gen  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import proposition_extraction as px  # noqa: E402
from agentmem_ref.runtime import typed_proposition as typed  # noqa: E402

PROTOCOL_ID = "currentness-oracle-ceiling-732-v1"
MODES = ("gold", "flag_blind", "slot_drift")
SUBJECT, ATTRIBUTE = "oracle subject", "oracle attribute"
OLD_VALUE, NEW_VALUE = "oracle value one", "oracle value two"
DRIFT_SUBJECT, DRIFT_ATTRIBUTE = "the oracle subject", "current oracle attribute"

# Gold flag per non-structural negative family (brief.md N1-N6, N11, N12). N12 covers both
# coexistence and embedded reports of someone else's change; either flag is a correct refusal
# reason, and the oracle sets only ``coexistent`` so the diagnostic does not double-count.
FAMILY_FLAGS: dict[str, tuple[str, ...]] = {
    "N1": ("attributed_to_other", "quoted_or_forwarded"),
    "N2": ("quoted_or_forwarded",),
    "N3": ("joke_or_sarcasm",),
    "N4": ("hedged",),
    "N5": ("conditional",),
    "N6": ("negated",),
    "N11": (),  # multi-valued: cardinality, not a flag
    "N12": ("coexistent",),
}
MULTI_FAMILIES = frozenset({"N11", "N12"})
VARIANT_FLAGS: dict[str, tuple[str, ...]] = {
    "hedge": ("hedged",),
    "attribution": ("attributed_to_other",),
    "conditional": ("conditional",),
    "coexistent": ("coexistent",),
}
MULTI_VARIANTS = frozenset({"coexistent"})


def _proposition(value: str, assertion: str, *, cardinality: str = "single", replaces: str | None = None,
                 flags: Sequence[str] = (), subject: str = SUBJECT, attribute: str = ATTRIBUTE) -> dict[str, Any]:
    return {"subject": subject, "attribute": attribute, "value": value, "assertion": assertion,
            "cardinality": cardinality, "replaces_value": replaces,
            "flags": {name: name in flags for name in typed.FLAGS}}


def newer_label(record: Mapping[str, Any], family: str, mode: str) -> dict[str, Any]:
    """The oracle's typed record for the newer write, from metadata only."""

    flags: tuple[str, ...] = ()
    multi = False
    if mode in ("gold", "slot_drift"):
        vtype = record.get("variant_type")
        if record.get("kind") == "must_change":
            flags, multi = VARIANT_FLAGS.get(vtype, ()), vtype in MULTI_VARIANTS
        else:  # base case or invariance variant: the base family's label
            flags, multi = FAMILY_FLAGS.get(family, ()), family in MULTI_FAMILIES
    drift = {"subject": DRIFT_SUBJECT, "attribute": DRIFT_ATTRIBUTE} if mode == "slot_drift" else {}
    return _proposition(NEW_VALUE, "change", cardinality="multi" if multi else "single",
                        replaces=OLD_VALUE, flags=flags, **drift)


class OracleExtractor:
    """A local ``PropositionExtractor`` answering from a per-record label table keyed by text."""

    extractor_id = "oracle-ceiling"

    def __init__(self, labels: Mapping[str, Mapping[str, Any]], mode: str) -> None:
        self.extractor_version = f"{PROTOCOL_ID}/{mode}"
        self.egress_policy = lambda _text: True  # local; nothing leaves the process
        self._labels = labels
        self.calls: list[dict[str, Any]] = []

    def extract(self, new_text: str, candidates: Sequence[Mapping[str, str]]) -> px.TypedExtraction:
        label = self._labels.get(new_text)
        texts = [item["text"] for item in candidates]
        self.calls.append({"new_text": new_text, "candidate_texts": texts})
        if label is None:
            output: dict[str, Any] = {"proposition": None, "updates_fact_uuid": None}
        else:
            link_text = label.get("link_to_candidate_text")
            link = next((item["fact_uuid"] for item in candidates if item["text"] == link_text), None)
            output = {"proposition": label["proposition"], "updates_fact_uuid": link}
        raw = json.dumps(output, sort_keys=True)
        return px.TypedExtraction(proposition=output["proposition"], updates_fact_uuid=output["updates_fact_uuid"],
                                  extractor_id=self.extractor_id, extractor_version=self.extractor_version,
                                  raw_output=raw, request_id=None, prompt_sha256=px.PROMPT_SHA256)


def labels_for(record: Mapping[str, Any], family: str, mode: str) -> dict[str, dict[str, Any]] | None:
    """Text -> oracle label for one record, or None when its texts are not unique (S0-like)."""

    writes = record["writes"]
    older, newer = writes[record["older_write"]]["text"], writes[record["newer_write"]]["text"]
    if len({w["text"] for w in writes}) != len(writes):
        return None
    table: dict[str, dict[str, Any]] = {older: {"proposition": _proposition(OLD_VALUE, "state")}}
    table[newer] = {"proposition": newer_label(record, family, mode), "link_to_candidate_text": older}
    return table


def run_with_oracle(record: Mapping[str, Any], family: str, mode: str) -> dict[str, Any]:
    labels = labels_for(record, family, mode)
    if labels is None:
        return {"stage": "S0", "reason": "oracle_invalid:duplicate_write_text"}
    extractor = OracleExtractor(labels, mode)

    def _open(root: str, handle: str, scope: str) -> AgentMemory:
        return AgentMemory.open(root, tenant=gen.TENANT, actor_id=gen.HANDLES[handle], scope=gen.SCOPES[scope],
                                purpose=gen.PURPOSE, proposition_extractor=extractor)

    original = gen._open
    gen._open = _open
    try:
        result = gen.run_record(dict(record))
    finally:
        gen._open = original
    older_text = record["writes"][record["older_write"]]["text"]
    newer_text = record["writes"][record["newer_write"]]["text"]
    newer_calls = [c for c in extractor.calls if c["new_text"] == newer_text]
    result.setdefault("observations", {})
    result["observations"]["oracle_older_in_candidates"] = (
        any(older_text in c["candidate_texts"] for c in newer_calls) if newer_calls else None)
    result["observations"]["oracle_extractor_calls"] = len(extractor.calls)
    return result


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attribution(results: Mapping[str, Mapping[str, Any]], ids: Sequence[str]) -> dict[str, int]:
    """Stage / reason counts, with S3 split by whether candidate generation offered the older fact."""

    counts: Counter = Counter()
    for cid in ids:
        r = results[cid]
        key = r["reason"]
        if r["stage"] == "S3":
            seen = (r.get("observations") or {}).get("oracle_older_in_candidates")
            key += ":older_not_in_candidates" if seen is False else ":older_in_candidates"
        counts[key] += 1
    return dict(sorted(counts.items()))


def diagnose(corpus_path: Path, variants_path: Path, selection_path: Path, mode: str) -> dict[str, Any]:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    variants = json.loads(variants_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    family_of = {case["case_id"]: case["family"] for case in corpus}
    results: dict[str, dict] = {}
    for case in corpus:
        results[case["case_id"]] = run_with_oracle(case, case["family"], mode)
    for variant in variants:
        if "na_reason" not in variant:
            results[variant["variant_id"]] = run_with_oracle(variant, family_of[variant["base_case_id"]], mode)
    scores = gen.score(corpus, variants, selection, results)
    # The measurement corpus is spent: no gate verdict is emitted from it (plan-732-remediation
    # non-goal "re-scoring the measurement corpus"). Only the counts are kept, for diagnosis.
    for key in ("verdict", "fail_reasons", "pass_criteria", "mixed_causes"):
        scores.pop(key, None)
    positive_ids = [c["case_id"] for c in corpus if c["family"] in gen.POSITIVE]
    negative_ids = [c["case_id"] for c in corpus if c["family"] in gen.N_FAMILIES]
    must_change = [v["variant_id"] for v in variants if "na_reason" not in v and v["kind"] == "must_change"]
    flip_by_type: dict[str, dict[str, int]] = {}
    for v in variants:
        if "na_reason" in v or v["kind"] != "must_change":
            continue
        entry = flip_by_type.setdefault(v["variant_type"], {"total": 0, "engaged": 0})
        entry["total"] += 1
        entry["engaged"] += results[v["variant_id"]]["stage"] == "S7"
    missing = sorted(cid for cid, r in results.items()
                     if (r.get("observations") or {}).get("oracle_older_in_candidates") is False)
    engaged_positive = [cid for cid in positive_ids if results[cid]["stage"] == "S7"]
    return {
        "candidate_generation": {
            "older_not_in_candidates": missing,
            "positive_engaged": len(engaged_positive),
            "positive_engaged_with_older_in_candidates": sum(
                1 for cid in engaged_positive if cid not in missing),
        },
        "protocol": {"id": PROTOCOL_ID, "mode": mode, "kind": "diagnostic_not_score",
                     "authority_effect": "none", "credential_used": False, "egress": "none"},
        "inputs": {"corpus_sha256": _sha(corpus_path), "variants_sha256": _sha(variants_path),
                   "selection_sha256": _sha(selection_path)},
        "scores": scores,
        "attribution": {
            "positive": attribution(results, positive_ids),
            "negative": attribution(results, negative_ids),
            "must_change": attribution(results, must_change),
        },
        "must_change_engaged_by_type": dict(sorted(flip_by_type.items())),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("variants", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = diagnose(args.corpus, args.variants, args.selection, args.mode)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    s = report["scores"]
    print(json.dumps({"mode": args.mode, "overall_recall": s["overall_recall"],
                      "structural_fe": s["structural_false_engagements"],
                      "non_structural_fe": s["non_structural_false_engagements"],
                      "m_inv": s["m_inv"], "m_flip": s["m_flip"], "m_attr": s["m_attr"],
                      "candidate_generation": {k: v for k, v in report["candidate_generation"].items()
                                               if k != "older_not_in_candidates"},
                      "attribution": report["attribution"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
