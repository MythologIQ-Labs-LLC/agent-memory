"""Provider outage probe. usage: python probe_outage.py <tree>"""
import json, sys, tempfile, os
from pathlib import Path
tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime.representation_onnx import RepresentationUnavailable  # noqa: E402
from agentmem_ref.runtime import vector_retrieval  # noqa: E402

FACTS = ["The spare house key is under the blue plant pot.", "The plumber fixed the leaking kitchen tap.",
         "We keep the car keys on the hook by the front door.", "The key safe code for Grandma's house is 4471.",
         "Our house insurance renews in May."]
Q = "Where is the spare key kept?"
rep = {}

def summary(r):
    ev = [d.get("ranking_evidence") or {} for d in r["admissions"].values() if "rank_position" in d]
    return {"policy": sorted({e.get("policy_version") for e in ev}), "fusion": sorted({str((e.get("fusion") or {}).get("status")) for e in ev}),
            "admitted": len(r["admitted"])}

with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as empty:
    # (a) failure at open
    for mode in ("auto", "required"):
        try:
            with AgentMemory.open(Path(tmp) / mode, tenant="t:o", actor_id="a:o", scope="s:o", purpose="o",
                                  semantic_retrieval=mode, representation_dir=empty) as m:
                for f in FACTS: m.remember("memory:x", f) if False else m.remember(f"memory:{abs(hash(f))%10**6}", f)
                r = m.recall(Q, budget=5, return_selection="ranked_prefix")
                rep[f"open_{mode}"] = {"opened": True, "posture": m.semantic_retrieval_posture()["status"], **summary(r)}
        except Exception as exc:
            rep[f"open_{mode}"] = {"opened": False, "error": type(exc).__name__, "msg": str(exc)[:100]}
    # (b) query-time failure during the route scan (query embedding) and (c) during fusion only
    root = Path(tmp) / "q"
    for label, exc_type in (("RepresentationUnavailable", RepresentationUnavailable), ("RuntimeError", RuntimeError)):
        for where in ("route_scan_query_embed", "route_scan_fact_embed", "fusion_similarities"):
            with AgentMemory.open(root, tenant="t:o", actor_id="a:o", scope="s:o", purpose="o", semantic_retrieval="required") as m:
                if not m.recall("warm", budget=1)["admitted"] and not any(True for _ in []):
                    pass
                for i, f in enumerate(FACTS):
                    m.remember(f"memory:{label}-{where}-{i}", f)
                retr = m._semantic["retriever"]
                prov = retr.representation
                orig = prov.embed
                newq = f"{Q} ({label} {where})"
                patch_sim = None
                if where == "route_scan_query_embed":
                    prov.embed = lambda text, _o=orig: (_ for _ in ()).throw(exc_type("provider down")) if text == newq else _o(text)
                elif where == "route_scan_fact_embed":
                    m.remember(f"memory:new-{label}", "A brand new note about the spare key under the mat.")
                    # clear the cached vector so the scan must embed this fact
                    prov.embed = lambda text, _o=orig: (_ for _ in ()).throw(exc_type("provider down")) if "under the mat" in text else _o(text)
                    retr.store._connection.execute("DELETE FROM vectors")
                else:
                    if hasattr(retr, "similarities"):
                        orig_sim = retr.similarities
                        retr.similarities = lambda *a, **k: (_ for _ in ()).throw(exc_type("provider down"))
                    else:
                        rep[f"{where}:{label}"] = "no similarities() on this tree (no fusion)"
                        continue
                try:
                    for sel in ("ranked_prefix", "relevance_sufficient"):
                        r = m.recall(newq, budget=5, return_selection=sel)
                        rep[f"{where}:{label}:{sel}"] = {"ok": True, **summary(r)}
                except Exception as exc:
                    rep[f"{where}:{label}"] = {"ok": False, "error": type(exc).__name__, "msg": str(exc)[:80]}
                prov.embed = orig
print(json.dumps(rep, indent=1))
