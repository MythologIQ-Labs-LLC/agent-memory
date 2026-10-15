"""Supplementary probes (asof window, written after probe set 1 to isolate an admission question; evaluator-authored)."""
import json
U = "user:probe"
def ops(old, new, t_old, t_new, ref):
    return [{"op": "remember", "ref": ref, "text": old, "scope": U, "observed_at": t_old},
            {"op": "correct", "ref": ref, "as": ref + "@new", "text": new, "scope": U, "replacement_kind": "state_change", "valid_from": t_new}]
asof = lambda t: {"mode": "as_of", "reference_time": t, "target_start": t}
S = [
 {"id": "w1", "category": "asof_window", "operations": ops("I work at Halden Robotics.", "I work at Vireo Health now.", "2021-01-01T00:00:00Z", "2024-01-01T00:00:00Z", "job"),
  "queries": [{"id": "w1-asof2022", "query": "Where do I work?", "must": ["job"], "may": [], "exclude": ["job@new"], "scope": U, "temporal_intent": asof("2022-06-01T00:00:00Z")},
              {"id": "w1-now", "query": "Where do I work?", "must": ["job@new"], "may": [], "exclude": ["job"], "scope": U},
              {"id": "w1-hist", "query": "Where did I work before?", "must": ["job"], "may": ["job@new"], "exclude": [], "scope": U, "temporal_intent": {"mode": "historical"}}]},
 {"id": "w2", "category": "asof_window", "operations": ops("Our home is a canal boat moored near Oxford.", "Our home is a terraced house in Reading.", "2020-01-01T00:00:00Z", "2023-01-01T00:00:00Z", "home"),
  "queries": [{"id": "w2-asof2021", "query": "What was our home like?", "must": ["home"], "may": [], "exclude": ["home@new"], "scope": U, "temporal_intent": asof("2021-06-01T00:00:00Z")},
              {"id": "w2-asof2021-para", "query": "Where were we living at that point?", "must": ["home"], "may": [], "exclude": ["home@new"], "scope": U, "temporal_intent": asof("2021-06-01T00:00:00Z")}]},
]
json.dump({"probe_set": "819-e-probes-2", "budget": 5, "scenarios": S}, open("probes2.json", "w"), indent=1)
