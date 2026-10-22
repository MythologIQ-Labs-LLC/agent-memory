"""Contention probe for the #786 CompetingWriters race, parameterised beyond the test (threads, writes,
rounds). Reports, per round, how many other-project handles hit the designed RuntimeCheckpointConflict,
how many failed closed at open (RuntimeRecoveryError, tolerated by the test), how many failed closed
*inside remember* with RuntimeRecoveryError (the full-suite failure signature), whether any other-project
write committed, and whether the owner's head survived. usage: race_probe.py <threads> <writes> <rounds>"""
import sys, tempfile, threading, json, collections
from agentmem_ref import AgentMemory
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict, RuntimeRecoveryError
sys.path.insert(0, "tests")
from tests.test_644_combined_independent import _prop

TENANT, ACTOR, QUERY = "tenant:c786", "agent:c786", "Orrin gateway region"
threads_n, writes_n, rounds_n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
totals = collections.Counter()
for r in range(rounds_n):
    tmp = tempfile.TemporaryDirectory(); root = tmp.name + "/m"
    def opn(scope):
        return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="c786")
    owner = opn("project:a")
    first = owner.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))["fact_uuid"]
    owner.close()
    counts = collections.Counter(); errors = []
    def run(scope, n):
        try:
            try:
                h = opn(scope)
            except RuntimeRecoveryError:
                counts["open_recovery_error"] += 1; return
            try:
                for i in range(n):
                    try:
                        out = h.remember("memory:a", f"{QUERY} is {scope}-{i}")
                    except RuntimeCheckpointConflict:
                        counts["checkpoint_conflict"] += 1; continue
                    except RuntimeRecoveryError as exc:
                        counts["remember_recovery_error"] += 1; errors.append(str(exc)); continue
                    if out["committed"]:
                        counts["committed_by_b"] += 1
                    else:
                        counts["refused"] += 1
            finally:
                try: h.close()
                except Exception as exc: counts["close_error"] += 1; errors.append("close: " + str(exc))
        except BaseException as exc:
            counts["other_error"] += 1; errors.append(repr(exc))
    ts = [threading.Thread(target=run, args=("project:b", writes_n)) for _ in range(threads_n)]
    for t in ts: t.start()
    for t in ts: t.join()
    owner = opn("project:a")
    head = owner._canonical_history("memory:a")["history"]["current_fact_uuid"]
    admitted = owner.recall(QUERY)["admitted"]
    owner.close(); tmp.cleanup()
    counts["head_moved"] += int(head != first); counts["admitted_not_first"] += int(admitted != [first])
    totals.update(counts)
    if counts["remember_recovery_error"] or counts["head_moved"] or counts["committed_by_b"]:
        print(f"round {r}: {dict(counts)} | {sorted(set(errors))[:2]}")
print("TOTAL", json.dumps(dict(totals), sort_keys=True))
