import sys, json, tempfile, subprocess, sqlite3, os
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from agentmem_ref.verification import TRANSITION_VERIFIER, VerifierRegistry
from tests.qualified_fixtures import corpus_for, rule
from tests.test_644_combined_independent import _prop, _evidence
Q = "Orrin gateway region"
del_corpus = corpus_for(rule(rule_id="rule:perm", target="memory:a", criterion="permanent-deletion", from_state="current", to_values=("deleted",)))
reg = VerifierRegistry(); vs = [del_corpus.verifier()]
reg.register(TRANSITION_VERIFIER, lambda item: any(v(item) for v in vs))
d = tempfile.mkdtemp(); root = d + "/m"
m = AgentMemory.open(root, tenant="tenant:c644", actor_id="agent:c644", scope="project:a", purpose="c644", verifier_registry=reg)
old = m.remember("memory:a", f"{Q} is Oslozzz", proposition=_prop("Oslozzz"))["fact_uuid"]
c = m.correct("memory:a", f"{Q} is Bergenzzz", evidence=_evidence(), risk_class="low", replacement_kind="state_change"); print("corr", c["committed"], c.get("refusal"))
ev = del_corpus.evidence_for(target_reference="memory:a", criterion="permanent-deletion", pre_state="current", proposed_value="deleted")
f = m.forget("memory:a", permanent=True, evidence=ev, risk_class="low")
print("permanent forget", f["committed"], f.get("refusal"), f.get("outcome"))
print("substrate get old/new", m.runtime.adapter._substrate.get_fact(old), m.runtime.adapter._substrate.get_fact(c["fact_uuid"]))
m.close()
files = subprocess.run(["grep", "-rlaF", "Oslozzz", root], capture_output=True, text=True).stdout.split()
print("files still containing deleted value bytes:", [os.path.relpath(x, root) for x in files])
files2 = subprocess.run(["grep", "-rlaF", "Bergenzzz", root], capture_output=True, text=True).stdout.split()
print("files containing deleted head bytes:", [os.path.relpath(x, root) for x in files2])
db = os.path.join(root, "agent-memory.sqlite3")
if os.path.exists(db):
    con = sqlite3.connect(db); cur = con.cursor()
    for (t,) in cur.execute("select name from sqlite_master where type='table'").fetchall():
        cols = [r[1] for r in cur.execute(f"pragma table_info({t})")]
        n = 0
        for row in cur.execute(f"select * from {t}"):
            if any(isinstance(v, (str, bytes)) and ("Oslozzz" in (v if isinstance(v, str) else v.decode("utf8", "ignore"))) for v in row): n += 1
        if n: print("  live rows with deleted value in table", t, n)
    print("  secure_delete pragma:", cur.execute("pragma secure_delete").fetchone())
