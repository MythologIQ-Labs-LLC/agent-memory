"""#774 follow-on control corpus "Fenmoor" (municipal library and makerspace), authored by the reviewer.

Frozen BEFORE the anchor guard or the automatic router is executed on it. Built to
stress routing and anchoring rather than to show gains:
  * paraphrased predecessor questions with NO interpreter cue (expected router misses),
  * a non-predecessor question that contains "before" (expected router false positive),
  * wrong-subject questions where the asked memory has no history and unrelated
    chains exist inside and outside the budget,
  * origin, why, event and current questions that must never be harmed,
  * deleted-memory and other-project predecessor questions (P0 controls).
The `expected_route` column records the reviewer's prediction of the frozen rule
(policy 0.1.0) before execution; it is NOT used for scoring.

Grades: 3 answers, 2 strong support, 1 topical context, 0 irrelevant.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = "2026-10-12T12:00:00Z"

EVENTS = [
    ("printer-pla", "retain", "printer", "The makerspace 3D printer uses PLA filament.", {}),
    ("printer-petg", "update", "printer", "The makerspace 3D printer now uses PETG filament.", {}),
    ("printer-asa", "update", "printer", "The makerspace 3D printer switched to ASA filament.", {}),
    ("hours-9", "retain", "hours", "The reading room opens at 9 in the morning.", {}),
    ("hours-830", "update", "hours", "The reading room now opens at 8:30 in the morning.", {}),
    ("loan-14", "retain", "loan", "The standard loan period for members is 14 days.", {}),
    ("loan-21", "update", "loan", "The standard loan period for members is now 21 days.", {}),
    ("why-loan", "retain", "why-loan", "The loan period was extended because course texts had long waiting lists.", {}),
    ("wifi-guest", "retain", "wifi", "The guest wifi network is called FenGuest.", {}),
    ("wifi-open", "update", "wifi", "The guest wifi network is now called FenOpen.", {}),
    ("laser", "retain", "laser", "The laser cutter requires a safety induction before first use.", {}),
    ("archive", "retain", "archive", "The local history archive moved to the basement in 2021.", {}),
    ("director", "retain", "director", "The Fenmoor library director is Ada Pike.", {}),
    ("chute-n", "retain", "chute", "The book returns chute is at the north door.", {}),
    ("chute-s", "update", "chute", "The book returns chute is now at the south door.", {}),
    ("chute-del", "delete", "chute", None, {}),
    ("refurb-300", "retain", "refurb", "The branch refurbishment budget is 300 thousand pounds.", {"project": "capital-programme"}),
    ("refurb-450", "update", "refurb", "The branch refurbishment budget is now 450 thousand pounds.", {}),
    ("fine-20", "retain", "fine", "The late return fine is 20 pence per day.", {}),
    ("fine-30", "update", "fine", "The late return fine is now 30 pence per day.", {}),
    ("fine-25", "correct", "fine", "The late return fine is 25 pence per day; 30 pence was entered by mistake.", {}),
]
FACTS = [e[0] for e in EVENTS if e[1] != "delete"]
PROHIBITED = ["chute-n", "chute-s", "refurb-300", "refurb-450"]
SUPERSEDED = ["printer-pla", "printer-petg", "hours-9", "loan-14", "wifi-guest", "fine-20", "fine-30"]

# id, query, intent, budget, grades, critical groups, stratum, expected_route (prediction only)
QUERIES = [
    ("F01", "Which filament did the makerspace printer use before ASA?", "historical", 3,
     {"printer-petg": 3, "printer-asa": 2, "printer-pla": 1}, [["printer-petg"]], "predecessor-cue-3rev", True),
    ("F02", "What were the reading room opening hours previously?", "historical", 3,
     {"hours-9": 3, "hours-830": 2}, [["hours-9"]], "predecessor-cue-2rev", True),
    ("F03", "What loan period did members get prior to the extension?", "historical", 3,
     {"loan-14": 3, "loan-21": 2, "why-loan": 1}, [["loan-14"]], "predecessor-cue-with-rationale", True),
    ("F04", "Which wifi network name was replaced by FenOpen?", "historical", 3,
     {"wifi-guest": 3, "wifi-open": 2}, [["wifi-guest"]], "predecessor-paraphrase-no-cue", False),
    ("F05", "What filament came right ahead of the one the printer has now?", "historical", 3,
     {"printer-petg": 3, "printer-asa": 2, "printer-pla": 1}, [["printer-petg"]], "predecessor-paraphrase-no-cue", False),
    ("F06", "What filament did the makerspace printer originally use?", "historical", 3,
     {"printer-pla": 3, "printer-petg": 1, "printer-asa": 1}, [["printer-pla"]], "origin-not-predecessor", False),
    ("F07", "Why was the loan period extended?", "historical", 3,
     {"why-loan": 3, "loan-21": 2, "loan-14": 1}, [["why-loan"]], "why", False),
    ("F08", "What is required before first use of the laser cutter?", "timeless", 2,
     {"laser": 3}, [["laser"]], "decoy-before-not-predecessor", True),
    ("F09", "What was the laser cutter induction rule before?", "historical", 3,
     {"laser": 1}, [], "wrong-subject-no-history", True),
    ("F10", "Who was the library director before?", "historical", 1,
     {"director": 1}, [], "wrong-subject-no-history-budget-1", True),
    ("F11", "Where was the book returns chute before?", "historical", 3,
     {}, [], "predecessor-deleted-memory", True),
    ("F12", "What was the branch refurbishment budget before?", "historical", 3,
     {}, [], "predecessor-other-project", True),
    ("F13", "What was the late return fine before the current rate?", "historical", 3,
     {"fine-20": 3, "fine-25": 2}, [["fine-20"]], "predecessor-past-error-correction", True),
    ("F14", "What filament does the makerspace printer use now?", "current", 3,
     {"printer-asa": 3}, [["printer-asa"]], "current", False),
    ("F15", "When did the local history archive move to the basement?", "historical", 3,
     {"archive": 3}, [["archive"]], "historical-event-not-predecessor", False),
    ("F16", "Which guest wifi name did we use earlier?", "historical", 3,
     {"wifi-guest": 3, "wifi-open": 2}, [["wifi-guest"]], "predecessor-cue-earlier", True),
]


def build():
    events = []
    for eid, op, memory, text, extra in EVENTS:
        e = {"id": eid, "op": op, "memory": memory}
        if text is not None:
            e["text"] = text
        for k in ("project", "tenant"):
            if k in extra:
                e[k] = extra[k]
        events.append(e)
    inputs = {"schema": "served-memory-lifecycle-v3", "reference_time": T, "tenant": "fenmoor",
              "project": "library-operations", "purpose": "library-operations-assistant", "events": events,
              "queries": [{"id": q, "query": text, "intent": intent, "budget": budget}
                          for q, text, intent, budget, *_ in QUERIES]}
    cases, strata, expected = [], {}, {}
    for qid, text, intent, budget, grades, groups, stratum, route in QUERIES:
        assert not set(grades) - set(FACTS), qid
        rel = {f: grades.get(f, 0) for f in FACTS}
        stale = sorted(SUPERSEDED) if intent == "current" else []
        eligible = [f for f, g in rel.items() if g >= 2 and f not in PROHIBITED and f not in stale]
        cases.append({"id": qid, "scenario": text, "intent": intent, "budget": budget, "relevance": rel,
                      "critical_groups": groups, "prohibited": list(PROHIBITED), "stale": stale,
                      "safe_answer_exists": bool(groups and eligible)})
        strata[qid] = stratum
        expected[qid] = route
    return inputs, {"schema": "served-memory-quality-v1", "cases": cases}, strata, expected


def main():
    inputs, gold, strata, expected = build()
    (HERE / "fenmoor-v1-input.v3.json").write_text(json.dumps(inputs, indent=2, sort_keys=True) + "\n")
    (HERE / "fenmoor-v1-gold.json").write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    (HERE / "fenmoor-v1-strata.json").write_text(json.dumps(strata, indent=2, sort_keys=True) + "\n")
    (HERE / "fenmoor-v1-expected-routing.json").write_text(json.dumps(
        {"policy_version": "0.1.0", "note": "reviewer prediction of the frozen rule, written before execution",
         "expected_route": expected}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
