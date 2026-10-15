"""Targeted adversarial probes with a fixed-cosine fake provider.

usage: python probe_fake.py <tree>
Runs the same probes on whichever tree is given; prints one JSON line per probe.
"""
import json
import math
import sys
import tempfile
from pathlib import Path
from unittest import mock

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import representation_onnx  # noqa: E402
from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec  # noqa: E402

TENANT, SCOPE, DIM = "tenant:rv", "user:rv", 8


class Table:
    TABLE: dict = {}
    spec = VectorRepresentationSpec(representation_ref="test:rv", representation_version="1.0.0",
                                    config_digest="sha256:" + "ab" * 32, dimensions=DIM, deterministic_rebuild=True)

    def __init__(self, model_dir=None):
        pass

    def embed(self, text):
        qs = sorted(self.TABLE)
        v = [1.0 if q == text else 0.0 for q in qs] if text in self.TABLE else [self.TABLE[q].get(text, 0.0) for q in qs]
        rem = 1.0 - sum(c * c for c in v)
        return tuple(v + [0.0] * (DIM - 1 - len(v)) + [math.sqrt(max(rem, 0.0))])


def ev(scope=SCOPE):
    s = pm.SkillArtifact(skill_id="skill:rv", version=1, purpose="apply a lifecycle change", scope=scope,
                         isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                         procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:rv",))
    return pm.evidence_for(s)


mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", Table).start()


def store(tmp, **kw):
    return AgentMemory.open(tmp, tenant=kw.pop("tenant", TENANT), actor_id="agent:rv", scope=kw.pop("scope", SCOPE),
                            purpose="rv", semantic_retrieval="required", **kw)


def names(refs, res):
    return [refs.get(u, "?" + u[:6]) for u in res["returned"]]


def sem(refs, res):
    out = []
    for u, d in res["admissions"].items():
        for h in d.get("route_provenance") or []:
            if "vector" in h["route_id"] or "semantic" in h["route_id"]:
                out.append((refs.get(u, "?"), round(h["raw_score"], 2), d.get("refusal")))
    return out


def report(name, **kv):
    print(json.dumps({"probe": name, **kv}))


# H1: explicit historical recall; a forgotten memory is the nearest neighbour.
def h1():
    q = "Which animal is scared of storms?"
    Table.TABLE = {q: {"Our old beagle used to hide from thunder.": 0.90, "Biscuit, our beagle, hides from thunder.": 0.70}}
    with tempfile.TemporaryDirectory() as tmp, store(tmp) as m:
        refs = {}
        for r, t in [("old", "Our old beagle used to hide from thunder."), ("a", "Biscuit, our beagle, hides from thunder.")]:
            refs[m.remember(r, t)["fact_uuid"]] = r
        assert m.forget("old", evidence=ev())["committed"]
        cur = m.recall(q, budget=10)
        hist = m.recall(q, budget=10, temporal_intent={"mode": "historical"})
        report("H1 historical, forgotten nearest", current=names(refs, cur), historical=names(refs, hist),
               historical_semantic=sem(refs, hist))


# H2: historical recall after an error correction; the corrected-as-false original is nearest.
def h2():
    q = "Where is my workplace?"
    orig, fix = "I am employed by Contoso Retail.", "Northwind Logistics took me on after Contoso Retail closed."
    Table.TABLE = {q: {orig: 0.90, fix: 0.70}}
    with tempfile.TemporaryDirectory() as tmp, store(tmp) as m:
        refs = {m.remember("job", orig)["fact_uuid"]: "job-orig"}
        o = m.correct("job", fix, evidence=ev())
        assert o["committed"], o
        refs[o["fact_uuid"]] = "job-fixed"
        cur = m.recall(q, budget=10)
        hist = m.recall(q, budget=10, temporal_intent={"mode": "historical"})
        report("H2 historical, error-corrected original nearest", current=names(refs, cur), historical=names(refs, hist),
               historical_semantic=sem(refs, hist))


# H3: as-of recall; a state-changed record outside the window is nearest.
def h3():
    q = "Which city is home?"
    old, new = "My flat was in Leeds.", "We moved into a house in York."
    Table.TABLE = {q: {old: 0.90, new: 0.70}}
    with tempfile.TemporaryDirectory() as tmp, store(tmp) as m:
        refs = {m.remember("home", old, observed_at="2022-01-01T00:00:00Z")["fact_uuid"]: "home-leeds"}
        o = m.correct("home", new, evidence=ev(), replacement_kind="state_change", valid_from="2024-01-01T00:00:00Z")
        assert o["committed"], o
        refs[o["fact_uuid"]] = "home-york"
        asof = m.recall(q, budget=10, temporal_intent={"mode": "as_of", "reference_time": "2025-06-01T00:00:00Z",
                                                        "target_start": "2025-06-01T00:00:00Z"})
        asof_old = m.recall(q, budget=10, temporal_intent={"mode": "as_of", "reference_time": "2023-06-01T00:00:00Z",
                                                            "target_start": "2023-06-01T00:00:00Z"})
        report("H3 as_of", as_of_2025=names(refs, asof), sem_2025=sem(refs, asof), as_of_2023=names(refs, asof_old),
               sem_2023=sem(refs, asof_old))


# H4: disputed memory nearest (current state and historical).
def h4():
    q = "Which animal is scared of storms?"
    bad, good = "The hamster panics whenever it thunders.", "Biscuit, our beagle, hides from thunder."
    Table.TABLE = {q: {bad: 0.90, good: 0.70}}
    with tempfile.TemporaryDirectory() as tmp, store(tmp) as m:
        refs = {m.remember("bad", bad)["fact_uuid"]: "bad", m.remember("good", good)["fact_uuid"]: "good"}
        d = m.dispute("bad", evidence=ev())
        cur = m.recall(q, budget=10)
        hist = m.recall(q, budget=10, temporal_intent={"mode": "historical"})
        report("H4 disputed nearest", dispute_committed=d.get("committed"), current=names(refs, cur),
               historical=names(refs, hist), historical_semantic=sem(refs, hist))


# H5: tie at the K boundary; is the choice stable across fresh stores?
def h5():
    q = "Who looks after the garden?"
    a, b = "Priya mows the lawn on Saturdays.", "Tomasz prunes the roses each spring."
    Table.TABLE = {q: {a: 0.70, b: 0.70}}
    seen = []
    for _ in range(8):
        with tempfile.TemporaryDirectory() as tmp, store(tmp) as m:
            refs = {m.remember("a", a)["fact_uuid"]: "a", m.remember("b", b)["fact_uuid"]: "b"}
            seen.append(tuple(names(refs, m.recall(q, budget=10))))
    report("H5 exact tie, 8 fresh stores", outcomes=sorted(set(seen)), counts={str(k): seen.count(k) for k in set(seen)})


# H6: ranked_prefix with the semantic route on; five semantically-only reachable facts.
def h6():
    q = "Who looks after the garden?"
    texts = [f"Helper {n} visits on day {n}." for n in range(5)]
    Table.TABLE = {q: {t: 0.70 - 0.01 * i for i, t in enumerate(texts)}}
    with tempfile.TemporaryDirectory() as tmp, store(tmp) as m:
        refs = {m.remember(f"h{i}", t)["fact_uuid"]: f"h{i}" for i, t in enumerate(texts)}
        rp = m.recall(q, budget=10, return_selection="ranked_prefix")
        rs = m.recall(q, budget=10)
        report("H6 ranked_prefix semantic on", ranked_prefix=names(refs, rp), relevance_sufficient=names(refs, rs))


# H7: empty store, and a store whose only memories are forgotten.
def h7():
    q = "Which pets do we have?"
    Table.TABLE = {q: {"Biscuit is our beagle.": 0.9}}
    with tempfile.TemporaryDirectory() as tmp, store(tmp) as m:
        e = m.recall(q, budget=10)
        m.remember("a", "Biscuit is our beagle.")
        m.forget("a", evidence=ev())
        f = m.recall(q, budget=10)
        fh = m.recall(q, budget=10, temporal_intent={"mode": "historical"})
        report("H7 empty/forgotten-only", empty=e["returned"], forgotten_only=f["returned"], forgotten_hist=fh["returned"],
               abstained=(f.get("return_policy") or {}).get("abstained"))


# H8: cross-tenant and cross-scope memories that are the nearest neighbours.
def h8():
    q = "Which pets do we have?"
    theirs, other_tenant, mine = "The neighbours' ferret sleeps in a hammock.", "A parrot named Kiwi lives here.", "Biscuit is our beagle."
    Table.TABLE = {q: {theirs: 0.95, other_tenant: 0.93, mine: 0.60}}
    with tempfile.TemporaryDirectory() as tmp:
        with store(tmp, scope="user:other") as o:
            o.remember("theirs", theirs)
        try:
            with store(tmp, tenant="tenant:other") as t:
                t.remember("ot", other_tenant)
            ot = "written"
        except Exception as exc:  # a root may be bound to one tenant
            ot = f"refused: {type(exc).__name__}"
        with store(tmp) as m:
            refs = {m.remember("mine", mine)["fact_uuid"]: "mine"}
            r = m.recall(q, budget=10)
            blob = json.dumps(r)
            report("H8 cross-scope/tenant nearest", other_tenant_write=ot, returned=names(refs, r),
                   leaks=[w for w in ("ferret", "parrot", "Kiwi") if w in blob], semantic=sem(refs, r))


# H9: shadow recall-control stop reason for an ordinary single-answer query.
def h9():
    q = "Where is my workplace?"
    t1, t2 = "Northwind Logistics employs me as head of analytics.", "Biscuit, our beagle, hides from thunder."
    Table.TABLE = {q: {t1: 0.70, t2: 0.10}}
    with tempfile.TemporaryDirectory() as tmp, store(tmp, recall_control="shadow") as m:
        m.remember("a", t1)
        m.remember("b", t2)
        r = m.recall(q, budget=10)
        rc = r["recall_control"]
        report("H9 shadow stop", counts=rc["route_candidate_counts"], stop=rc["actual_stop"])


for p in (h1, h2, h3, h4, h5, h6, h7, h8, h9):
    try:
        p()
    except Exception as exc:
        report(p.__name__, error=f"{type(exc).__name__}: {exc}")
