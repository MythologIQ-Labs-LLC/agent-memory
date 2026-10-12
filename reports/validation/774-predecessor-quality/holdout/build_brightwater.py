"""#774 held-out corpus "Brightwater" (regional water utility), authored by the reviewer.

Frozen BEFORE the #774 selector is executed on it. Not used to design the
#774 logic (which was designed on the generic histories in
reference/tests/test_774_governed_predecessor.py). Writes v3 lifecycle input,
gold, strata and the caller-declared routing file next to this script.

Grades: 3 answers, 2 strong support, 1 topical context, 0 irrelevant.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = "2026-10-12T12:00:00Z"

EVENTS = [
    ("pumps-2", "retain", "pumps", "The Kessel Road pumping station operates two duty pumps.", {}),
    ("pumps-3", "update", "pumps", "The Kessel Road pumping station now operates three duty pumps after the 2022 expansion.", {}),
    ("pumps-4", "update", "pumps", "Kessel Road pumping station operates four duty pumps since the 2025 refit.", {}),
    ("chl-05", "retain", "chlorine", "The free chlorine target at the reservoir outlet is 0.5 milligrams per litre.", {}),
    ("chl-08", "update", "chlorine", "The free chlorine target at the reservoir outlet was raised to 0.8 milligrams per litre.", {}),
    ("chl-07", "correct", "chlorine", "The free chlorine target at the reservoir outlet is 0.7 milligrams per litre; the 0.8 figure was a data-entry mistake.", {}),
    ("scada-ww", "retain", "scada", "Telemetry and SCADA run on Wonderware InTouch.", {}),
    ("scada-i7", "update", "scada", "Telemetry and SCADA moved to Ignition 7.", {}),
    ("scada-i80", "update", "scada", "Telemetry and SCADA were upgraded to Ignition 8.0.", {}),
    ("scada-i81", "update", "scada", "Telemetry and SCADA were upgraded to Ignition 8.1.", {}),
    ("scada-i83", "update", "scada", "Telemetry and SCADA now run Ignition 8.3.", {}),
    ("bill-q", "retain", "billing", "Customers receive water bills every quarter.", {}),
    ("bill-2m", "update", "billing", "Customers now receive water bills every two months.", {}),
    ("why-bill", "retain", "why-billing", "Billing moved to a two-month cycle because customers complained that quarterly bills were too large to budget for.", {}),
    ("sap", "retain", "sap", "The billing system migration to SAP finished in March 2024.", {}),
    ("meter-arq", "retain", "meter", "Smart meter readings are collected over the Arqiva network.", {}),
    ("meter-itron", "update", "meter", "Smart meter readings are now collected over the Itron mesh network.", {}),
    ("meter-del", "delete", "meter", None, {}),
    ("budget-2m", "retain", "budget", "The Kessel Road pumping station upgrade budget is 2 million pounds.", {"project": "capital-works"}),
    ("budget-4m", "update", "budget", "The Kessel Road pumping station upgrade budget is now 4 million pounds.", {}),
    ("harbour-pumps", "retain", "harbour-pumps", "The Kessel Road pumping station operates six duty pumps.", {"tenant": "harbourcity"}),
    ("canteen", "retain", "canteen", "The Kessel Road depot canteen opens at 7 in the morning.", {}),
    ("leak", "retain", "leak", "Leak detection on trunk mains uses acoustic loggers.", {}),
]
FACTS = [e[0] for e in EVENTS if e[1] != "delete"]
PROHIBITED = ["meter-arq", "meter-itron", "budget-2m", "budget-4m", "harbour-pumps"]
SUPERSEDED = ["pumps-2", "pumps-3", "chl-05", "chl-08", "scada-ww", "scada-i7", "scada-i80", "scada-i81", "bill-q"]

# id, query, intent, budget, grades, critical groups, stratum, caller declares predecessor relationship?
QUERIES = [
    ("B01", "How many duty pumps did Kessel Road run before the latest change?", "historical", 3,
     {"pumps-3": 3, "pumps-4": 2, "pumps-2": 1, "harbour-pumps": 1}, [["pumps-3"]], "predecessor-3rev", True),
    ("B02", "What was the reservoir outlet chlorine target before the current value?", "historical", 3,
     {"chl-05": 3, "chl-07": 2}, [["chl-05"]], "predecessor-past-error-correction", True),
    ("B03", "Which telemetry platform version preceded the one in use now?", "historical", 3,
     {"scada-i81": 3, "scada-i83": 2, "scada-i80": 1, "scada-i7": 1, "scada-ww": 1}, [["scada-i81"]], "predecessor-5rev", True),
    ("B04", "How often were customers billed before the current cycle?", "historical", 3,
     {"bill-q": 3, "bill-2m": 2, "why-bill": 1}, [["bill-q"]], "predecessor-2rev", True),
    ("B05", "Which network collected smart meter readings before?", "historical", 3,
     {}, [], "predecessor-deleted-memory", True),
    ("B06", "What happened with the billing system migration?", "historical", 3,
     {"sap": 3}, [["sap"]], "historical-not-predecessor", False),
    ("B07", "Why did the billing frequency change?", "historical", 3,
     {"why-bill": 3, "bill-2m": 2, "bill-q": 1}, [["why-bill"]], "historical-why", False),
    ("B08", "How many duty pumps does Kessel Road operate now?", "current", 3,
     {"pumps-4": 3}, [["pumps-4"]], "current-after-chain", False),
    ("B09", "What is the reservoir outlet chlorine target?", "current", 2,
     {"chl-07": 3}, [["chl-07"]], "current-after-error-correction", False),
    ("B10", "How is leak detection done on trunk mains?", "timeless", 2,
     {"leak": 3}, [["leak"]], "single-fact", False),
    ("B11", "What was the pumping station upgrade budget before?", "historical", 3,
     {}, [], "predecessor-other-project", True),
    ("B12", "Which telemetry platform did Brightwater use before Ignition 8.0?", "historical", 3,
     {"scada-i7": 3, "scada-i80": 2, "scada-ww": 1, "scada-i81": 1, "scada-i83": 1}, [["scada-i7"]],
     "predecessor-of-older-version", True),
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
    inputs = {"schema": "served-memory-lifecycle-v3", "reference_time": T, "tenant": "brightwater",
              "project": "operations", "purpose": "utility-operations-assistant", "events": events,
              "queries": [{"id": q, "query": text, "intent": intent, "budget": budget}
                          for q, text, intent, budget, *_ in QUERIES]}
    cases, strata, routed = [], {}, []
    for qid, text, intent, budget, grades, groups, stratum, predecessor in QUERIES:
        assert not set(grades) - set(FACTS), qid
        rel = {f: grades.get(f, 0) for f in FACTS}
        stale = sorted(SUPERSEDED) if intent == "current" else []
        eligible = [f for f, g in rel.items() if g >= 2 and f not in PROHIBITED and f not in stale]
        cases.append({"id": qid, "scenario": text, "intent": intent, "budget": budget, "relevance": rel,
                      "critical_groups": groups, "prohibited": list(PROHIBITED), "stale": stale,
                      "safe_answer_exists": bool(groups and eligible)})
        strata[qid] = stratum
        if predecessor:
            routed.append(qid)
    return inputs, {"schema": "served-memory-quality-v1", "cases": cases}, strata, routed


def main():
    inputs, gold, strata, routed = build()
    (HERE / "brightwater-v1-input.v3.json").write_text(json.dumps(inputs, indent=2, sort_keys=True) + "\n")
    (HERE / "brightwater-v1-gold.json").write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    (HERE / "brightwater-v1-strata.json").write_text(json.dumps(strata, indent=2, sort_keys=True) + "\n")
    routing = {
        "relationship": "immediate_predecessor",
        "note": ("Caller-declared routing, written before any #774 execution. Declared where the "
                 "question asks for the value that held before a later value of the same thing. "
                 "Halcyon/Cedarline entries were declared from question wording before #774 ran on them."),
        "brightwater-v1": routed,
        "halcyon-v1.1": ["H02", "H14"],
        "cedarline-v1.1": ["C02", "C07", "C15"],
    }
    (HERE / "routing-declarations.json").write_text(json.dumps(routing, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
