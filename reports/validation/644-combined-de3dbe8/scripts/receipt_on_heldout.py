"""Receipt false-positive check over the frozen 126 held-out scenarios (harness imported, unmodified)."""
import sys, tempfile, hashlib, json
sys.path.insert(0, sys.argv[1])
src = open(sys.argv[1] + "/heldout_bench.py", "rb").read()
assert hashlib.sha256(src).hexdigest().startswith("25ce88eb")
import heldout_bench as H
ok = bad = crash = 0
for cat in H.CATS:
    for ent, vals in zip(H.ENTITIES, H.VALUES):
        with tempfile.TemporaryDirectory() as d:
            m, rel, lexical = H.build(cat, ent, vals, d + "/m")
            try:
                pl = H.ControlledRecallPlanner(m.runtime.adapter, controller=H.Fixed(lexical)); ctx = m._handle_recall_context()
                res = m.runtime.durable_runtime.run_governed_read(lambda: pl.recall(f"{ent[0]} {ent[1]}", ctx))
                if res.observation_unchanged(): ok += 1
                else: bad += 1; print("FALSE TAMPER", cat, ent)
            except Exception as e:
                crash += 1; print("CRASH", cat, type(e).__name__, e)
            finally:
                m.close()
print(json.dumps({"verified": ok, "false_tamper": bad, "crash": crash}))
