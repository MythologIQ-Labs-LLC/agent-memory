"""Temporal-ordering probe (reviewer-authored).

usage: python probe_temporal.py <tree> <off|required> <ranked_prefix|relevance_sufficient> <out.json>

Pairs of conflicting statements with IDENTICAL BM25 against the query (same token count, same
query-word overlap), so under 3.4.0 every relevance stage ties and the temporal stage decides.
Families:
  open_current   both declared valid_from only (2023 vs 2025), caller-declared current + reference_time
  lang_current   same pairs, query-language explicit current ("... now?"), no declared intent
  asof_2024      as_of 2024-06 (older applicable, newer prospectively applicable)
  historical     historical window 2023-2024
  unspecified    same texts written with observed_at only, no intent (incidental newer-first)
  crossfact      "I live in X" then "I have moved and now live in Y", caller-declared current
"""
import json, sys, tempfile
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402

semantic, selection, out = sys.argv[2], sys.argv[3], Path(sys.argv[4])
TENANT, ACTOR, SCOPE = "tenant:rvt", "agent:rvt", "user:rvt"
NOW = "2026-10-16T00:00:00Z"
PAIRS = [
 ("car", "What car do we drive?", "We drive a silver Ford Focus.", "We drive a blue Kia Niro."),
 ("manager", "Who is my manager?", "My manager is Joanna Pike.", "My manager is Rahul Mehta."),
 ("isp", "Who is our broadband provider?", "Our broadband provider is Virgin.", "Our broadband provider is Zen."),
 ("school", "Which school do the kids attend?", "The kids attend Northfield Primary.", "The kids attend Ashgrove Academy."),
 ("meds", "What medication do I take every morning?", "I take sertraline every morning.", "I take citalopram every morning."),
 ("dentist", "Who is our dentist?", "Our dentist is Dr Hale.", "Our dentist is Dr Moss."),
 ("bank", "Who do we bank with?", "We bank with Barclays.", "We bank with Monzo."),
 ("teacher", "Who is Ella's teacher?", "Ella's teacher is Mrs Grant.", "Ella's teacher is Mr Boyd."),
 ("gym", "Which gym do I use?", "I use the PureGym gym.", "I use the Nuffield gym."),
 ("phone", "What phone do I have?", "I have an iPhone 11 phone.", "I have a Pixel 8 phone."),
]
FILLER = [
 "The front door sticks when it rains.", "We repainted the hallway a pale green last spring.",
 "The upstairs radiator makes a ticking noise.", "Our recycling goes out every other Thursday.",
 "Mum likes crosswords and solves the Saturday one in pen.", "Dad walks to the newsagent every morning.",
 "My cousin Freya lives in Leeds and teaches piano.", "The council tax is paid by direct debit.",
 "We keep spare light bulbs in the under-stairs cupboard.", "The kids' swimming lessons are on Wednesdays.",
 "The car insurance renews in February.", "Ella is learning the clarinet at school.",
 "Our neighbour Pat feeds the cat when we travel.", "I keep receipts in a shoebox in the study.",
 "The pharmacy does repeat prescriptions.", "Parking at the station costs six pounds a day.",
]


def run_family(family):
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        kw = {} if semantic == "off" else {"semantic_retrieval": semantic}
        with AgentMemory.open(tmp, tenant=TENANT, actor_id=ACTOR, scope=SCOPE, purpose="rvt", **kw) as m:
            for i, t in enumerate(FILLER):
                assert m.remember(f"memory:f{i}", t)["committed"]
            ids = {}
            for key, q, old, new in PAIRS:
                if family == "unspecified":
                    o = m.remember(f"memory:{key}-old", old, observed_at="2023-02-01T00:00:00Z")
                    n = m.remember(f"memory:{key}-new", new, observed_at="2025-09-01T00:00:00Z")
                elif family == "crossfact":
                    continue
                else:
                    o = m.remember(f"memory:{key}-old", old, valid_from="2023-02-01T00:00:00Z")
                    n = m.remember(f"memory:{key}-new", new, valid_from="2025-09-01T00:00:00Z")
                assert o["committed"] and n["committed"], (o, n)
                ids[key] = (o["fact_uuid"], n["fact_uuid"])
            queries = []
            if family == "crossfact":
                for key, q, old, new in [
                    ("live", "Where do I live?", "I live in Denver.", "I have moved and now live in Boston."),
                    ("work", "Where do I work?", "I work at Acme Labs.", "I no longer work at Acme Labs; I work at Globex now."),
                ]:
                    o = m.remember(f"memory:{key}-old", old); n = m.remember(f"memory:{key}-new", new)
                    ids[key] = (o["fact_uuid"], n["fact_uuid"])
                    queries.append((key, q, {"mode": "current"}, NOW, "new"))
            else:
                for key, q, old, new in PAIRS:
                    if family == "open_current":
                        queries.append((key, q, {"mode": "current"}, NOW, "new"))
                    elif family == "lang_current":
                        queries.append((key, q.rstrip("?") + " now?", None, NOW, "new"))
                    elif family == "asof_2024":
                        queries.append((key, q, {"mode": "as_of", "target_start": "2024-06-01T00:00:00Z"}, "2024-06-01T00:00:00Z", "old"))
                    elif family == "historical":
                        queries.append((key, q, {"mode": "historical", "target_start": "2023-01-01T00:00:00Z", "target_end": "2024-12-31T00:00:00Z"}, None, "old"))
                    elif family == "unspecified":
                        queries.append((key, q, None, None, "new"))
            for key, q, intent, ref_time, preferred in queries:
                rkw = {"budget": 10, "return_selection": selection}
                if intent:
                    rkw["temporal_intent"] = intent
                if ref_time:
                    rkw["reference_time"] = ref_time
                r = m.recall(q, **rkw)
                old_u, new_u = ids[key]
                ranked = r["admitted"]
                ev = {u: (r["admissions"].get(u) or {}).get("ranking_evidence") or {} for u in (old_u, new_u)}
                pos = {lab: (ranked.index(u) + 1 if u in ranked else None) for lab, u in (("old", old_u), ("new", new_u))}
                pref_first = None if None in pos.values() else (pos[preferred] < pos["old" if preferred == "new" else "new"])
                rows.append({
                    "family": family, "key": key, "query": q, "preferred": preferred, "ranks": pos,
                    "preferred_first": pref_first,
                    "returned_first": [("old" if u == old_u else "new" if u == new_u else "other") for u in r["returned"][:2]],
                    "intent_mode": ev[new_u].get("query_intent_basis") or None,
                    "applicability": {lab: ev[u].get("temporal_applicability") for lab, u in (("old", old_u), ("new", new_u))},
                    "bm25": {lab: ev[u].get("lexical_relevance_score") for lab, u in (("old", old_u), ("new", new_u))},
                    "routes": {lab: ev[u].get("routes") for lab, u in (("old", old_u), ("new", new_u))},
                    "dense": {lab: (ev[u].get("fusion") or {}).get("dense_similarity") for lab, u in (("old", old_u), ("new", new_u))},
                    "fused": {lab: (ev[u].get("fusion") or {}).get("fused_score") for lab, u in (("old", old_u), ("new", new_u))},
                    "ordered_by": {lab: ev[u].get("ordered_before_next_by") for lab, u in (("old", old_u), ("new", new_u))},
                    "policy": ev[new_u].get("policy_version"),
                })
    return rows


rows = []
for fam in ("open_current", "lang_current", "asof_2024", "historical", "unspecified", "crossfact"):
    rows += run_family(fam)
out.write_text(json.dumps({"tree": str(tree), "semantic": semantic, "selection": selection, "rows": rows}, indent=1))
from collections import Counter
c = Counter((r["family"], r["preferred_first"]) for r in rows)
print(out.name, dict(sorted(c.items(), key=str)))
