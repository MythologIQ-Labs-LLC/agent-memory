"""F: the semantic set channel (and plural_answer) can never fire at the shipped constants.
python3 repro_set_channel.py <worktree>"""
import sys, json
sys.path.insert(0, sys.path[0]); import fakes; fakes.setup(sys.argv[1])
from agentmem_ref.runtime import return_selection as rs
FACTS = {"m:dog": "Biscuit the beagle hides during thunderstorms.",
         "m:cat": "Miso, the tabby we adopted, sleeps all day.",
         "m:fish": "Four neon tetras swim in the kitchen aquarium.",
         "m:car": "We keep the Corolla in the garage."}
for q in ("Which pets do we have?", "How many pets do we have?", "List all our pets."):
    table = {q: {FACTS["m:dog"]: 0.80, FACTS["m:cat"]: 0.72, FACTS["m:fish"]: 0.62, FACTS["m:car"]: 0.10}}
    s = fakes.Store(fakes.table_provider(table)); s.seed(FACTS)
    res, ret = s.recall(q)
    bases = {s.refs[u]: d["return_selection"]["basis"] for u, d in res["admissions"].items() if "return_selection" in d}
    sc = res["return_policy"].get("semantic_channel")
    print(f"{q!r}: returned={ret} bases={bases}")
    print(f"   plural_answer={sc and sc['plural_answer']} needs_several={res['return_policy'].get('information_requirement',{}).get('needs_several')}")
    s.close()
if hasattr(rs, "SEMANTIC_SET_FLOOR"):
    print("constants: abs", rs.SEMANTIC_ABSOLUTE_FLOOR, "single", rs.SEMANTIC_SINGLE_MARGIN,
          "set", rs.SEMANTIC_SET_FLOOR, "set_margin", rs.SEMANTIC_SET_MARGIN,
          "-> set branch reachable:", rs.SEMANTIC_SET_FLOOR < rs.SEMANTIC_ABSOLUTE_FLOOR or rs.SEMANTIC_SET_MARGIN > rs.SEMANTIC_SINGLE_MARGIN)
