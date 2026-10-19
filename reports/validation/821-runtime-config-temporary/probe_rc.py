"""Fail-first probe for the fixed runtime-config.json temp name. usage: probe_rc.py TREE"""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
TREE = Path(sys.argv[1]).resolve()
CHILD = r'''
import io, os, signal, sys, time, builtins
sys.path.insert(0, sys.argv[1] + "/reference")
root, mode = sys.argv[2], sys.argv[3]
def is_tmp(p):
    try: b = os.path.basename(os.fspath(p))
    except TypeError: return False
    return "runtime-config.json" in b and b != "runtime-config.json"
_io, _osopen, _rep = io.open, os.open, os.replace
def io_open(p, m="r", *a, **k):
    f = _io(p, m, *a, **k)
    if mode == "kill_after_tmp_open" and is_tmp(p) and any(c in m for c in "wax+"): os.kill(os.getpid(), signal.SIGKILL)
    return f
def os_open(p, flags, *a, **k):
    fd = _osopen(p, flags, *a, **k)
    if mode == "kill_after_tmp_open" and is_tmp(p) and flags & (os.O_WRONLY | os.O_RDWR): os.kill(os.getpid(), signal.SIGKILL)
    return fd
def replace(s, d, *a, **k):
    if mode == "stall_replace" and os.path.basename(os.fspath(d)) == "runtime-config.json": time.sleep(1.5)
    return _rep(s, d, *a, **k)
io.open = builtins.open = io_open; os.open = os_open; os.replace = replace
from agentmem_ref import AgentMemory
with AgentMemory.open(root, tenant="tenant:rc", actor_id="agent:rc", scope="project:rc", purpose="rc") as m:
    print("OK", m.remember("memory:" + mode, mode + " fact").get("committed"))
'''
def child(root, mode, timeout=60):
    try:
        p = subprocess.run([sys.executable, "-c", CHILD, str(TREE), str(root), mode], capture_output=True, text=True, timeout=timeout)
        return {"rc": p.returncode, "out": (p.stdout + p.stderr).strip()[-200:]}
    except subprocess.TimeoutExpired:
        return {"rc": "HANG", "out": f"no exit within {timeout} s"}
res = {"tree": subprocess.run(["git", "-C", str(TREE), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()}
races = []
for r in range(3):
    root = Path(tempfile.mkdtemp(prefix="rc-")) / "store"; root.mkdir()
    a = subprocess.Popen([sys.executable, "-c", CHILD, str(TREE), str(root), "stall_replace"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.5); b = child(root, "kill_after_tmp_open"); oa, ea = a.communicate(timeout=60)
    cfg = root / "runtime-config.json"
    races.append({"A_rc": a.returncode, "A": (oa + ea).strip()[-160:], "B_rc": b["rc"], "config_bytes": cfg.stat().st_size if cfg.exists() else None,
                  "reopen": child(root, "none")})
res["race"] = races
root = Path(tempfile.mkdtemp(prefix="rc-")) / "store"; root.mkdir(); target = root.parent / "target.txt"; target.write_text("SENTINEL\n")
os.symlink(target, root / ".runtime-config.json.tmp")
c = child(root, "none"); cfg = root / "runtime-config.json"
res["symlink"] = {"open": c, "target_unchanged": target.read_text() == "SENTINEL\n", "config_is_symlink": cfg.is_symlink()}
root = Path(tempfile.mkdtemp(prefix="rc-")) / "store"; root.mkdir(); os.mkfifo(root / ".runtime-config.json.tmp")
res["fifo"] = {"open": child(root, "none", timeout=15)}
print(json.dumps(res, indent=1))
