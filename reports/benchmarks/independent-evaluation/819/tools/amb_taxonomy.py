"""Independent failure taxonomy for AMB PrecisionMemBench single-turn retrieval results.

Uses only AMB's own result file (scored by AMB) plus the frozen seed/cases to classify
each relevantBeliefs-tier error. It never re-scores: pass/fail comes from AMB.
"""
import collections, json, re, sys
DS = "/tmp/eval/amb/.datasets/precisionmembench"
beliefs = {b["_id"]: b for b in json.load(open(f"{DS}/beliefs.seed.json"))}
cases = {c["caseId"]: c for c in json.load(open(f"{DS}/retrieval.cases.json"))}


def classify_extra(bid, case):
    b = beliefs.get(bid)
    if b is None:
        return "unknown_id"
    user = case.get("userId", "test-user")
    if b["user_id"] != user:
        return "cross_user"
    if b.get("superseded_by") or b.get("resolved_at") or b.get("epistemic_status") == "superseded":
        return "superseded_or_resolved"
    if not set(b.get("scope", [])) & set(case["scope"]) and "user:universal" not in b.get("scope", []):
        return "out_of_scope"
    if b["type"] == "open_question":
        return "type_misroute_open_question"
    return "in_scope_not_relevant"


def analyse(path):
    res = json.load(open(path))
    out = []
    for r in res["results"]:
        case = cases[r["query_id"]]
        reasons = [s.strip() for s in (r.get("judge_reason") or "").split(";") if s.strip()]
        kinds = collections.Counter()
        extras = []
        for s in reasons:
            m = re.match(r"(unexpected belief in relevantBeliefs|forbidden belief surfaced|missing expected belief|expected belief missing \(shouldInclude\)|missing pinned belief|missing expected question|ranking|orderedBefore|relevantBeliefs count)[: ]*(\S*)", s)
            kind = m.group(1) if m else s.split(":")[0]
            kinds[kind] += 1
            if kind in ("unexpected belief in relevantBeliefs", "forbidden belief surfaced") and m:
                extras.append(classify_extra(m.group(2), case))
        out.append({"case": r["query_id"], "category": case["category"], "correct": bool(r["correct"]),
                    "blank_query": not case["query"].strip(), "reason_kinds": dict(kinds),
                    "extra_classes": dict(collections.Counter(extras)),
                    "precision": (r.get("meta") or {}).get("retrieval_precision"), "recall": (r.get("meta") or {}).get("retrieval_recall"),
                    "returned_relevant": len((r.get("meta") or {}).get("relevant_beliefs") or [])})
    return res, out


def main():
    res, rows = analyse(sys.argv[1])
    failed = [x for x in rows if not x["correct"]]
    print(json.dumps({"total": len(rows), "correct": len(rows) - len(failed), "failed": len(failed),
        "failed_with_unexpected_or_forbidden": sum(1 for x in failed if x["extra_classes"]),
        "failed_only_missing": sum(1 for x in failed if not x["extra_classes"]),
        "extra_belief_classes_total": dict(sum((collections.Counter(x["extra_classes"]) for x in failed), collections.Counter())),
        "failed_cases_by_dominant_extra_class": dict(collections.Counter(max(x["extra_classes"], key=x["extra_classes"].get) if x["extra_classes"] else "no_extra" for x in failed)),
        "reason_kinds_total": dict(sum((collections.Counter(x["reason_kinds"]) for x in failed), collections.Counter())),
        "by_category": {c: f"{sum(1 for x in rows if x['category']==c and x['correct'])}/{sum(1 for x in rows if x['category']==c)}" for c in sorted({x['category'] for x in rows})}}, indent=1))
    if len(sys.argv) > 2:
        json.dump(rows, open(sys.argv[2], "w"), indent=1)


if __name__ == "__main__":
    main()
