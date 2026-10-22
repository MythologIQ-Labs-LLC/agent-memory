"""P6: tampering still fails recovery; close() publishes nothing (rows), even after refused/ungoverned acts."""
import json, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403


def tamper(name, sql):
    root, m = fresh()
    m.recall("deploy window")
    m.close()
    c = sqlite3.connect(str(Path(root) / "agent-memory.sqlite3"))
    c.executescript(sql)
    c.commit(); c.close()
    print(f"tamper {name:38s} -> {try_reopen(root)}")


tamper("fact text", "UPDATE facts SET fact_text='The deploy window is Friday.';")
tamper("id_counter +1", "UPDATE agent_memory_meta SET value=CAST(value AS INTEGER)+1 WHERE key='id_counter';")
tamper("id_counter -1", "UPDATE agent_memory_meta SET value=CAST(value AS INTEGER)-1 WHERE key='id_counter';")
tamper("drop last journal row", "DELETE FROM runtime_journal WHERE generation=(SELECT MAX(generation) FROM runtime_journal);")
tamper("runtime_state generation-1",
       "UPDATE runtime_state SET payload_json=json_set(payload_json,'$.generation',json_extract(payload_json,'$.generation')-1);")
tamper("governance_residual edit", "UPDATE governance_residual SET payload_json=replace(payload_json,'tenant:p','tenant:q');" if False else
       "DELETE FROM governance_log WHERE rowid=(SELECT MAX(rowid) FROM governance_log);")

# close() publishes nothing, after a refused act and after an ungoverned in-memory mutation
root, m = fresh()
before = rows(root)
for act in (lambda: m.runtime.adapter.governed_recall("deploy", m._handle_recall_context()),
            lambda: m.runtime.adapter.record_correction("memory:x"),
            lambda: m.runtime.adapter.set_shared_domain_members("shared:x", ("agent:evil",))):
    try:
        act()
    except Exception:  # noqa: BLE001
        pass
m.close()
after = rows(root)
print("close() after refused + ungoverned acts: rows changed:", [t for t in after if after[t] != before.get(t)])
m2 = opened(root)
st = m2.runtime.adapter.export_checkpoint_state()
print("reopened: shared_domain_members =", st.get("shared_domain_members"), "state_version =", st.get("state_version"))
m2.close()
