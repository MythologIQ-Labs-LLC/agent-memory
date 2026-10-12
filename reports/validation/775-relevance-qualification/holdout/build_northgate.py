"""#775 subject-collision corpus "Northgate" (two-clinic healthcare group), reviewer-authored.

Frozen BEFORE any relevance-qualification prototype is run on it. Stresses:
  * two entities sharing attributes (opening hours, records system, parking, lead)
  * shared attribute with DIFFERENT reasons per entity
  * questions about an entity that does not exist in the reader's scope
  * valid answers phrased with different terminology (synonyms / paraphrase)
  * other-project and other-tenant facts about a third clinic
  * query words that overlap the wrong subject
Grades: 3 answers, 2 strong support, 1 topical context, 0 irrelevant.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = "2026-10-12T12:00:00Z"
EVENTS = [
    ("rv-hours", "Riverside Clinic opens at 8 in the morning on weekdays.", {}),
    ("hl-hours", "Hilltop Clinic opens at 9 in the morning on weekdays.", {}),
    ("rv-ehr", "Riverside Clinic keeps patient charts in the Medway electronic records system.", {}),
    ("hl-ehr", "Hilltop Clinic keeps patient charts in the Medway electronic records system.", {}),
    ("rv-ehr-why", "Riverside Clinic switched to electronic charts after a 2021 flood destroyed its paper files.", {}),
    ("hl-ehr-why", "Hilltop Clinic switched to electronic charts after a regulator audit criticised illegible handwriting.", {}),
    ("rv-lead", "Dr. Amara Osei is the medical lead at Riverside Clinic.", {}),
    ("hl-lead", "Dr. Tomasz Wilk is the medical lead at Hilltop Clinic.", {}),
    ("rv-park", "Riverside Clinic has no on-site parking; patients use the Mill Lane car park.", {}),
    ("hl-park", "Hilltop Clinic has twenty free parking spaces behind the building.", {}),
    ("rv-xray", "Riverside Clinic does not offer X-ray imaging; patients are referred to the county hospital.", {}),
    ("phlebotomy", "Blood tests at Hilltop Clinic are drawn by phlebotomists between 8 and 11 each morning.", {}),
    ("triage", "Both clinics triage same-day requests by telephone before booking an appointment.", {}),
    ("flu", "Seasonal flu vaccination at Riverside Clinic runs from October to December.", {}),
    ("group-it", "The Northgate group help desk handles password resets for both clinics.", {}),
    ("eastgate-plan", "The planned Eastgate Clinic will open at 7 in the morning.", {"project": "expansion"}),
    ("other-tenant", "Riverside Clinic opens at 6 in the morning.", {"tenant": "southbank"}),
    ("canteen", "The Northgate staff canteen serves lunch from noon.", {}),
]
FACTS = [e[0] for e in EVENTS]
PROHIBITED = ["eastgate-plan", "other-tenant"]

QUERIES = [
    ("N01", "What time does Hilltop Clinic open?", "current", 2, {"hl-hours": 3, "rv-hours": 0, "other-tenant": 0}, [["hl-hours"]], "shared-attribute"),
    ("N02", "When does the Riverside practice start seeing patients in the morning?", "current", 2, {"rv-hours": 3}, [["rv-hours"]], "paraphrase"),
    ("N03", "Why did Hilltop Clinic move to electronic charts?", "timeless", 2, {"hl-ehr-why": 3, "hl-ehr": 1}, [["hl-ehr-why"]], "shared-reason-wrong-subject"),
    ("N04", "Why did Riverside go paperless?", "timeless", 2, {"rv-ehr-why": 3, "rv-ehr": 1}, [["rv-ehr-why"]], "synonym-answer"),
    ("N05", "Who is the medical lead at Hilltop Clinic?", "current", 2, {"hl-lead": 3}, [["hl-lead"]], "shared-attribute"),
    ("N06", "Who is the medical lead at Eastgate Clinic?", "current", 2, {}, [], "no-answer-missing-entity"),
    ("N07", "When does Eastgate Clinic open?", "current", 2, {"eastgate-plan": 3}, [], "no-answer-other-project"),
    ("N08", "Where should Riverside patients park?", "current", 2, {"rv-park": 3}, [["rv-park"]], "shared-attribute"),
    ("N09", "Can I get an X-ray at Hilltop Clinic?", "current", 2, {}, [], "no-answer-wrong-subject"),
    ("N10", "Does Riverside do radiography?", "current", 2, {"rv-xray": 3}, [["rv-xray"]], "synonym-answer"),
    ("N11", "When are blood samples taken at Hilltop?", "current", 2, {"phlebotomy": 3}, [["phlebotomy"]], "synonym-answer"),
    ("N12", "How are same-day requests handled at Hilltop Clinic?", "current", 2, {"triage": 3}, [["triage"]], "shared-fact-both-entities"),
    ("N13", "When does flu vaccination run at Hilltop Clinic?", "current", 2, {"flu": 1}, [], "no-answer-wrong-subject"),
    ("N14", "Which records system does Hilltop Clinic use?", "current", 2, {"hl-ehr": 3, "rv-ehr": 0}, [["hl-ehr"]], "shared-attribute-same-value"),
    ("N15", "Who resets my password?", "current", 2, {"group-it": 3}, [["group-it"]], "paraphrase"),
    ("N16", "What is the Riverside Clinic phone number?", "current", 2, {}, [], "no-answer-missing-attribute"),
]


def build():
    events = []
    for eid, text, extra in EVENTS:
        e = {"id": eid, "op": "retain", "memory": eid, "text": text}
        e.update({k: v for k, v in extra.items() if k in ("project", "tenant")})
        events.append(e)
    inputs = {"schema": "served-memory-lifecycle-v3", "reference_time": T, "tenant": "northgate",
              "project": "clinics", "purpose": "clinic-operations-assistant", "events": events,
              "queries": [{"id": q, "query": t, "intent": i, "budget": b} for q, t, i, b, *_ in QUERIES]}
    cases, strata = [], {}
    for qid, text, intent, budget, grades, groups, stratum in QUERIES:
        assert not set(grades) - set(FACTS), qid
        rel = {f: grades.get(f, 0) for f in FACTS}
        eligible = [f for f, g in rel.items() if g >= 2 and f not in PROHIBITED]
        cases.append({"id": qid, "scenario": text, "intent": intent, "budget": budget, "relevance": rel,
                      "critical_groups": groups, "prohibited": list(PROHIBITED), "stale": [],
                      "safe_answer_exists": bool(groups and eligible)})
        strata[qid] = stratum
    return inputs, {"schema": "served-memory-quality-v1", "cases": cases}, strata


def main():
    inputs, gold, strata = build()
    for name, doc in (("input.v3", inputs), ("gold", gold), ("strata", strata)):
        (HERE / f"northgate-v1-{name}.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
