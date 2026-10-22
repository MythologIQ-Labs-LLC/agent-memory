"""R9: witness invariants under concurrent writers with random SIGKILLs.
usage: python r9.py <tree> <seconds> <writers> <seed>
A monitor samples, in recovery's order, the witness file and then the database's committed
generation and journal. Invariants: the witness is always parseable (never empty or partial), never
leads the committed generation, and its digest matches the journal at its generation. Also measured:
regressions (witness value decreasing between samples), maximum lag, orphaned temporaries, and
whether the store reopens at the end."""
import json, os, random, signal, sqlite3, subprocess, sys, tempfile, threading, time
from pathlib import Path
T, SECS, W, SEED = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
random.seed(SEED)
O = dict(tenant="tenant:r9", actor_id="agent:r9", scope="project:r9", purpose="r9 probe")
WRITER = r'''
import sys, json
sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref import AgentMemory
root, wid, O = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
i = 0
while True:
    i += 1
    try:
        with AgentMemory.open(root, **O) as m:
            m.remember(f"memory:{wid}-{i}", f"writer {wid} fact {i}")
    except Exception as e:
        print(type(e).__name__, str(e)[:120], flush=True)
'''
SEED_OPEN = r'''
import sys, json
sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref import AgentMemory
try:
    with AgentMemory.open(sys.argv[2], **json.loads(sys.argv[3])) as m:
        if len(sys.argv) > 4: m.remember("memory:seed", "seed fact")
    print("OPENS")
except Exception as e:
    print("REFUSED", type(e).__name__, str(e)[:200])
'''
stats = dict(samples=0, unparseable=0, leads=0, digest_mismatch=0, regressions=0, max_lag=0, kills=0)
examples = []
with tempfile.TemporaryDirectory() as t:
    root = Path(t) / "s"
    subprocess.run([sys.executable, "-c", SEED_OPEN, T, str(root), json.dumps(O), "seed"], capture_output=True)
    db, wp = root / "agent-memory.sqlite3", root / "generation-witness.json"
    stop = threading.Event()

    def monitor():
        last = None
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
        while not stop.is_set():
            raw = wp.read_bytes()
            try:
                w = json.loads(raw); g, d = w["generation"], w["journal_record_digest"]
            except Exception:
                stats["unparseable"] += 1
                if len(examples) < 5: examples.append({"unparseable": raw[:80].decode(errors="replace")})
                time.sleep(0.002); continue
            try:
                cur = conn.execute("SELECT json_extract(payload_json,'$.generation') FROM runtime_state").fetchone()[0]
                j = conn.execute("SELECT payload_json FROM runtime_journal WHERE generation = ?", (g,)).fetchone()
            except sqlite3.OperationalError:
                continue
            stats["samples"] += 1
            if g > cur: stats["leads"] += 1
            if g > 0 and (j is None or json.loads(j[0]).get("record_digest") != d): stats["digest_mismatch"] += 1
            if last is not None and g < last: stats["regressions"] += 1
            stats["max_lag"] = max(stats["max_lag"], cur - g)
            last = g
            time.sleep(0.002)
        conn.close()

    procs = {}
    def spawn(k):
        procs[k] = subprocess.Popen([sys.executable, "-c", WRITER, T, str(root), str(k), json.dumps(O)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for k in range(W): spawn(k)
    th = threading.Thread(target=monitor); th.start()
    end = time.monotonic() + SECS; n = W
    while time.monotonic() < end:
        time.sleep(random.uniform(0.05, 0.4))
        k = random.choice(list(procs))
        procs[k].send_signal(signal.SIGKILL); procs[k].wait(); stats["kills"] += 1
        del procs[k]; spawn(n); n += 1
    for p in procs.values(): p.send_signal(signal.SIGKILL); p.wait()
    stop.set(); th.join()
    orphans = sorted(p.name for p in root.glob(".generation-witness.json*"))
    r = subprocess.run([sys.executable, "-c", SEED_OPEN, T, str(root), json.dumps(O)], capture_output=True, text=True)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    final = conn.execute("SELECT json_extract(payload_json,'$.generation') FROM runtime_state").fetchone()[0]; conn.close()
    print(json.dumps({"tree": Path(T).name, "seed": SEED, "secs": SECS, "writers": W, **stats,
                      "final_generation": final, "witness_bytes": wp.stat().st_size,
                      "orphan_temporaries": len(orphans), "reopen": r.stdout.strip()[-200:], "examples": examples}))
