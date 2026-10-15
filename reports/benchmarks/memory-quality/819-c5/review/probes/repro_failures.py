"""Determinism / degenerate-vector / provider-failure probes with an offline fake provider.
python3 repro_failures.py <worktree>"""
import sys, math, json
sys.path.insert(0, sys.path[0]); import fakes; fakes.setup(sys.argv[1])
FACTS = {"m:dog": "Biscuit the beagle hides during thunderstorms.",
         "m:cat": "Miso, the tabby we adopted, sleeps all day.",
         "m:car": "We keep the Corolla in the garage."}
Q = "Which pets do we have?"
TABLE = {Q: {FACTS["m:dog"]: 0.80, FACTS["m:cat"]: 0.78, FACTS["m:car"]: 0.10}}

def run(label, provider_cls, q=Q, sel="relevance_sufficient", budget=10, facts=FACTS):
    s = fakes.Store(provider_cls); s.seed(facts)
    provider_cls.calls.clear() if hasattr(provider_cls, "calls") else None
    try:
        res, ret = s.recall(q, budget=budget, sel=sel)
        sc = res["return_policy"].get("semantic_channel")
        print(f"{label}: returned={ret} abstained={res['return_policy'].get('abstained')} best_sim={sc and sc['best_similarity']}"
              f" query_embeds={sum(1 for c in getattr(provider_cls,'calls',[]) if c == q)}")
    except Exception as exc:
        print(f"{label}: RAISED {type(exc).__name__}: {exc}")
    s.close()

Base = fakes.table_provider(TABLE)
run("baseline", Base)

# 1. provider fails on the 2nd embedding of the query (i.e. after candidate discovery succeeded)
class FailSecondQuery(Base):
    n = 0
    def embed(self, text):
        if text == Q:
            FailSecondQuery.n += 1
            if FailSecondQuery.n == 2:
                raise RuntimeError("provider crashed mid-recall")
        return super().embed(text)
run("provider fails on 2nd query embed", FailSecondQuery)

# 2. provider returns NaN for the query on its 2nd call only
class NanSecondQuery(Base):
    n = 0
    def embed(self, text):
        v = super().embed(text)
        if text == Q:
            NanSecondQuery.n += 1
            if NanSecondQuery.n == 2:
                return tuple(float("nan") for _ in v)
        return v
run("NaN query vector on 2nd call", NanSecondQuery)

# 3. wrong dimension for the query on its 2nd call only
class DimSecondQuery(Base):
    n = 0
    def embed(self, text):
        v = super().embed(text)
        if text == Q:
            DimSecondQuery.n += 1
            if DimSecondQuery.n == 2:
                return v[:-1]
        return v
run("dimension mismatch on 2nd call", DimSecondQuery)

# 4. zero query vector (degenerate)
class ZeroQuery(Base):
    def embed(self, text):
        v = super().embed(text)
        return tuple(0.0 for _ in v) if text == Q else v
run("zero query vector", ZeroQuery)

# 5. zero fact vector for the dog
class ZeroDog(Base):
    def embed(self, text):
        v = super().embed(text)
        return tuple(0.0 for _ in v) if text == FACTS["m:dog"] else v
run("zero dog vector", ZeroDog)

# 6. a query vector that drifts slightly between calls (non-deterministic provider)
class Jitter(Base):
    n = 0
    def embed(self, text):
        v = super().embed(text)
        if text == Q:
            Jitter.n += 1
            return tuple(c + (1e-3 * Jitter.n if i == 7 else 0) for i, c in enumerate(v))
        return v
run("jittering query vector", Jitter)

# 7. empty store
s = fakes.Store(Base)
res, ret = s.recall(Q)
print("empty store:", ret, "abstained", res["return_policy"].get("abstained"), "semantic_channel" in res["return_policy"])
s.close()

# 8. ranked_prefix and budget
run("ranked_prefix", Base, sel="ranked_prefix")
run("budget=1", Base, budget=1)
