"""Independent adversarial probes (v2: stronger C/D stress, set before any repair was seen) for #821 R-1 (generation-witness temp files) and its neighbourhood.

usage: python adv821.py TREE OUT.json [--only A1,B,...] [--reps N]
Implementation-agnostic: faults are injected at the OS boundary (os.open, io.open, os.fsync, os.replace)
for any file in the store whose name contains "generation-witness" (temp = anything but the final name).
Author: independent qualification session_011h1ADQyj3ZTu9UHgBAhocF. Not part of the implementation's tests.
"""
import json, os, random, shutil, signal, stat, subprocess, sys, tempfile, time
from pathlib import Path

TREE = Path(sys.argv[1]).resolve(); OUT = sys.argv[2]
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
REPS = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 3
WIT = "generation-witness.json"
TENANT, ACTOR, SCOPE = "tenant:adv821", "agent:adv821", "project:adv821"

CHILD = r'''
import errno, io, json, os, random, signal, sys, time, builtins
sys.path.insert(0, sys.argv[1] + "/reference")
root, role, mode, fact = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
WIT = "generation-witness.json"
def is_temp(p):
    try: b = os.path.basename(os.fspath(p))
    except TypeError: return False
    return "generation-witness" in b and b != WIT
def fdpath(fd):
    try: return os.readlink(f"/proc/self/fd/{fd}")
    except OSError: return ""
def die(): os.kill(os.getpid(), signal.SIGKILL)
_os_open, _io_open, _fsync, _replace = os.open, io.open, os.fsync, os.replace
def os_open(p, flags, *a, **k):
    fd = _os_open(p, flags, *a, **k)
    if mode == "kill_after_temp_open" and is_temp(p) and flags & (os.O_WRONLY | os.O_RDWR): die()
    return fd
def io_open(p, m="r", *a, **k):
    f = _io_open(p, m, *a, **k)
    if mode == "kill_after_temp_open" and is_temp(p) and any(c in m for c in "wax+"): die()
    return f
def fsync(fd):
    path = fdpath(fd)
    if is_temp(path):
        if mode == "kill_at_temp_fsync": die()
        if mode == "enospc_at_temp_fsync": raise OSError(errno.ENOSPC, "No space left on device (injected)")
    if mode == "kill_at_dir_fsync" and os.path.isdir(path) and os.path.exists(os.path.join(path, WIT)): die()
    return _fsync(fd)
def replace(s, d, *a, **k):
    if os.path.basename(os.fspath(d)) == WIT:
        if mode == "delay_witness_replace": time.sleep(1.5)
        if mode == "kill_before_witness_replace": die()
        if mode == "log_witness":
            time.sleep(random.uniform(0, 0.05))
            try: v = json.loads(open(s, "rb").read())["generation"]
            except Exception: v = None
            with open(os.path.join(root, "..", f"wlog-{os.getpid()}.txt"), "a") as h: h.write(f"{time.time()} {v}\n")
    return _replace(s, d, *a, **k)
os.open, io.open, builtins.open, os.fsync, os.replace = os_open, io_open, io_open, fsync, replace
from agentmem_ref import AgentMemory
n = int(os.environ.get("ADV_ITER", "1"))
for i in range(n):
    try:
        with AgentMemory.open(root, tenant="tenant:adv821", actor_id="agent:adv821", scope="project:adv821", purpose="adv821") as m:
            out = m.remember(f"memory:{fact}-{i}", f"{fact} fact number {i}")
        if out.get("committed"):
            with _io_open(os.path.join(root, "..", f"ack-{os.getpid()}.txt"), "a") as h: h.write(f"{fact}-{i}\n"); h.flush(); _fsync(h.fileno())
            print("ACK", f"{fact}-{i}", flush=True)
        else:
            print("NOTCOMMITTED", f"{fact}-{i}", flush=True)
    except Exception as exc:
        print("REFUSED", type(exc).__name__, str(exc)[:160], flush=True)
'''


def child(root, role, mode, fact, iters=1, wait=True, timeout=120):
    env = dict(os.environ, ADV_ITER=str(iters), PYTHONHASHSEED="0")
    p = subprocess.Popen([sys.executable, "-c", CHILD, str(TREE), str(root), role, mode, fact],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if not wait: return p
    try: o, e = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); o, e = p.communicate(); return {"rc": "TIMEOUT", "out": o[-400:], "err": e[-400:]}
    return {"rc": p.returncode, "out": o[-400:], "err": e[-400:]}


def reopen(root, attempts=1):
    code = r'''
import sys, json; sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref import AgentMemory
try:
    with AgentMemory.open(sys.argv[2], tenant="tenant:adv821", actor_id="agent:adv821", scope="project:adv821", purpose="adv821") as m:
        r = m.recall("fact number", budget=500)
        print(json.dumps({"ok": True, "admitted": len(r.get("admitted") or [])}))
except Exception as exc:
    print(json.dumps({"ok": False, "error": type(exc).__name__ + ": " + str(exc)[:220]}))
'''
    res = None
    for _ in range(attempts):
        try:
            o = subprocess.run([sys.executable, "-c", code, str(TREE), str(root)], capture_output=True, text=True, timeout=60).stdout.strip().splitlines()
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "HANG: reopen+recall did not finish within 60 s"}
        res = json.loads(o[-1]) if o else {"ok": False, "error": "no output"}
        if res["ok"]: break
    return res


def facts_present(root, facts):
    code = r'''
import sys, json; sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref import AgentMemory
with AgentMemory.open(sys.argv[2], tenant="tenant:adv821", actor_id="agent:adv821", scope="project:adv821", purpose="adv821") as m:
    out = {}
    for f in json.loads(sys.argv[3]):
        r = m.recall(f.replace("-", " fact number "), budget=50)
        out[f] = len(r.get("admitted") or []) > 0
    print(json.dumps(out))
'''
    try:
        o = subprocess.run([sys.executable, "-c", code, str(TREE), str(root), json.dumps(facts)], capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"error": "HANG"}
    try: return json.loads(o.stdout.strip().splitlines()[-1])
    except Exception: return {"error": o.stderr[-300:]}


def witness_state(root):
    w = Path(root) / WIT
    st = {"exists": w.exists() or w.is_symlink(), "is_symlink": w.is_symlink()}
    if w.exists() and not w.is_symlink():
        raw = w.read_bytes(); st["bytes"] = len(raw); st["mode"] = oct(stat.S_IMODE(w.stat().st_mode))
        try: st["generation"] = json.loads(raw)["generation"]
        except Exception: st["generation"] = "UNPARSEABLE"
    st["temps"] = sorted(p.name for p in Path(root).iterdir() if "generation-witness" in p.name and p.name != WIT)
    return st


def fresh(base, name):
    root = Path(base) / name / "store"; root.parent.mkdir(parents=True, exist_ok=True)
    child(root, "seed", "none", "seed")
    return root


def run():
    R = {"tree": str(TREE), "head": subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "cases": {}}
    base = tempfile.mkdtemp(prefix="adv821-")
    want = lambda k: ONLY is None or k in ONLY
    # A: the R-1 cross-process race. A delays its rename; B dies / fails at a temp-file step meanwhile.
    for key, bmode in (("A1", "kill_after_temp_open"), ("A2", "kill_at_temp_fsync"), ("A3", "enospc_at_temp_fsync")):
        if not want(key): continue
        reps = []
        for r in range(REPS):
            root = fresh(base, f"{key}-{r}")
            pa = child(root, "A", "delay_witness_replace", "alpha", wait=False)
            time.sleep(0.5)
            b = child(root, "B", bmode, "beta")
            oa, ea = pa.communicate(timeout=120)
            ws = witness_state(root); ro = reopen(root)
            fp = facts_present(root, ["alpha-0", "beta-0"]) if ro["ok"] else None
            reps.append({"A_rc": pa.returncode, "A_out": oa.strip()[-120:], "B_rc": b["rc"], "B_out": b["out"].strip()[-120:], "witness": ws, "reopen": ro, "facts": fp})
        R["cases"][key] = {"b_fault": bmode, "reps": reps, "reopen_ok": sum(x["reopen"]["ok"] for x in reps), "n": len(reps)}
    # B: kill at each step of record() in one writer; then 20 more generations.
    if want("B"):
        steps = {}
        for bmode in ("kill_after_temp_open", "kill_at_temp_fsync", "kill_before_witness_replace", "kill_at_dir_fsync"):
            root = fresh(base, f"B-{bmode}")
            c = child(root, "K", bmode, "kappa")
            ws1 = witness_state(root); ro1 = reopen(root)
            fp = facts_present(root, ["kappa-0"]) if ro1["ok"] else None
            more = child(root, "M", "none", "more", iters=20)
            ws2 = witness_state(root); ro2 = reopen(root)
            steps[bmode] = {"rc": c["rc"], "after_kill": {"witness": ws1, "reopen": ro1, "facts": fp}, "after_20": {"witness": ws2, "reopen": ro2, "acks": more["out"].count("ACK")}}
        R["cases"]["B"] = steps
    # C: concurrent writers with random SIGKILLs.
    if want("C"):
        runs = []
        for r in range(REPS):
            root = fresh(base, f"C-{r}"); rnd = random.Random(821 + r)
            procs = [child(root, f"W{i}", "none", f"w{r}{i}", iters=60, wait=False) for i in range(8)]
            killed = 0; t0 = time.time()
            while any(p.poll() is None for p in procs) and time.time() - t0 < 600:
                time.sleep(rnd.uniform(0.05, 0.4))
                live = [p for p in procs if p.poll() is None]
                if live and rnd.random() < 0.6:
                    os.kill(rnd.choice(live).pid, signal.SIGKILL); killed += 1
            for p in procs:
                try: p.communicate(timeout=60)
                except Exception: p.kill()
            acks = []
            for f in Path(root).parent.glob("ack-*.txt"): acks += f.read_text().split()
            ws = witness_state(root); ro = reopen(root)
            fp = facts_present(root, acks) if ro["ok"] else None
            runs.append({"killed": killed, "acks": len(acks), "witness": ws, "reopen_first_try": ro,
                         "acked_missing": (sum(1 for v in fp.values() if v is False) if isinstance(fp, dict) and "error" not in fp else fp)})
        R["cases"]["C"] = {"runs": runs, "reopen_ok": sum(x["reopen_first_try"]["ok"] for x in runs), "n": len(runs)}
    # D: witness monotonicity across processes (no kills) + stale-witness acceptance/refusal.
    if want("D"):
        root = fresh(base, "D")
        procs = [child(root, f"L{i}", "log_witness", f"d{i}", iters=40, wait=False) for i in range(6)]
        for p in procs: p.communicate(timeout=600)
        events = []
        for f in Path(root).parent.glob("wlog-*.txt"):
            for line in f.read_text().split("\n"):
                if line.strip(): t, v = line.split(); events.append((float(t), None if v == "None" else int(v)))
        events.sort(); seq = [v for _, v in events if v is not None]
        regress = sum(1 for a, b in zip(seq, seq[1:]) if b < a)
        ws = witness_state(root); ro = reopen(root)
        # stale but genuine witness (older generation of this store) must be accepted
        R["cases"]["D"] = {"witness_writes": len(seq), "regressions": regress, "final_witness": ws, "reopen": ro}
    # E: hostile pre-planted temp path (symlink / FIFO at the predictable frozen name).
    if want("E"):
        out = {}
        root = fresh(base, "E-symlink"); target = Path(base) / "E-target.txt"; target.write_text("SENTINEL-DO-NOT-TOUCH\n")
        planted = root / f".{WIT}.tmp"; os.symlink(target, planted)
        c = child(root, "S", "none", "sym")
        out["symlink"] = {"child": c["out"].strip()[-120:], "target_unchanged": target.read_text() == "SENTINEL-DO-NOT-TOUCH\n",
                          "target_now": target.read_text()[:80], "witness": witness_state(root), "reopen": reopen(root)}
        root = fresh(base, "E-fifo"); planted = root / f".{WIT}.tmp"; os.mkfifo(planted)
        c = child(root, "F", "none", "fifo", timeout=20)
        out["fifo"] = {"child_rc": c["rc"], "child": (c.get("out") or "").strip()[-120:], "witness": witness_state(root), "reopen": reopen(root)}
        R["cases"]["E"] = out
    # F/G: published witness mode; empty / truncated witness must still be refused.
    if want("G"):
        out = {}
        for kind, payload in (("empty", b""), ("truncated", b'{"schema": "agent-memory-sqlite-generation-witness/1", "gener')):
            root = fresh(base, f"G-{kind}"); w = root / WIT
            if not w.exists(): out[kind] = {"note": "no witness on this tree"}; continue
            out[kind + "_mode_before"] = oct(stat.S_IMODE(w.stat().st_mode))
            w.write_bytes(payload); out[kind] = reopen(root)
        R["cases"]["G"] = out
    shutil.rmtree(base, ignore_errors=True)
    json.dump(R, open(OUT, "w"), indent=1)
    summ = {k: ({"reopen_ok": v.get("reopen_ok"), "n": v.get("n")} if isinstance(v, dict) and "n" in v else "see json") for k, v in R["cases"].items()}
    print(json.dumps({"head": R["head"][:10], "summary": summ}))


run()
