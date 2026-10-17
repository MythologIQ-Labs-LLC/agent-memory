"""Run a command, record an execution identity JSON beside its output (argv, cwd, exit, wall, child CPU, peak RSS, env, host).

Usage: run_logged.py RECORD_PREFIX CMD...   -> writes RECORD_PREFIX.exec.json and RECORD_PREFIX.log
"""
import json, os, platform, resource, subprocess, sys, time
from datetime import datetime, timezone

prefix, cmd = sys.argv[1], sys.argv[2:]
started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
t0 = time.monotonic()
with open(prefix + ".log", "wb") as log:
    rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)
wall = time.monotonic() - t0
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
keys = ["PYTHONHASHSEED", "AGENT_MEMORY_REPRESENTATION_DIR", "HF_HUB_OFFLINE", "OMP_NUM_THREADS", "VIRTUAL_ENV"]
rec = {
    "argv": cmd, "cwd": os.getcwd(), "exit_status": rc, "started_utc": started,
    "wall_seconds": round(wall, 3), "user_cpu_seconds": round(ru.ru_utime, 3),
    "system_cpu_seconds": round(ru.ru_stime, 3), "peak_rss_mib": round(ru.ru_maxrss / 1024, 1),
    "env": {k: os.environ.get(k) for k in keys},
    "secrets_present": {k: bool(os.environ.get(k)) for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "HF_TOKEN")},
    "host": {"platform": platform.platform(), "cpu_count": os.cpu_count(), "python": platform.python_version()},
}
json.dump(rec, open(prefix + ".exec.json", "w"), indent=2)
sys.exit(rc)
