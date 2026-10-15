#!/usr/bin/env python3
"""Run one comparator command in a clean, credential-free environment and record its execution.

Writes ``<prefix>.exec.json``, ``<prefix>.stdout`` and ``<prefix>.stderr``. The record has the
same fields as the existing ``*.exec.json`` files under ``reports/benchmarks/runs/``: argv, cwd,
an allowlisted environment, host, start time, exit status, wall and CPU seconds, peak RSS of the
command's process tree, and whether any inference/hosting credential was visible to it (none
may be). It never scores, edits or summarises results.

Example::

    python scripts/record_comparator_execution.py --prefix runs/x/hindsight-500 --user benchrun \\
      --env HINDSIGHT_SOURCE_ROOT=/tmp/hindsight-source --cwd /tmp/work -- \\
      /tmp/venv/bin/python reference/run_longmemeval_resumable.py ...
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import pwd
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RECORDED_ENV = ("HF_HOME", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "JEV_MEM_SOURCE_ROOT",
                "PYTHONHASHSEED", "VIRTUAL_ENV", "OMP_NUM_THREADS", "HOME")
SECRETS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TYPESAFE_API_KEY", "HF_TOKEN", "GEMINI_API_KEY",
           "GOOGLE_API_KEY", "GROQ_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
           "GH_TOKEN", "GITHUB_TOKEN", "LLM_API_KEY")
PASSTHROUGH = ("PATH", "LANG", "LC_ALL", "TZ", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
               "https_proxy", "http_proxy", "no_proxy", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
               "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--user", help="run the command as this unprivileged user")
    parser.add_argument("--env", action="append", default=[], help="KEY=VALUE for the command")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")

    env = {key: os.environ[key] for key in PASSTHROUGH if key in os.environ}
    for item in args.env:
        key, _, value = item.partition("=")
        env[key] = value
    preexec = None
    if args.user:
        record = pwd.getpwnam(args.user)
        env.update(USER=record.pw_name, LOGNAME=record.pw_name)
        env.setdefault("HOME", record.pw_dir)  # an explicit --env HOME=... wins (e.g. a separate pg0 home)

        def preexec() -> None:  # drop to the unprivileged user before exec
            os.setgroups([])
            os.setgid(record.pw_gid)
            os.setuid(record.pw_uid)

    args.prefix.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    with open(f"{args.prefix}.stdout", "wb") as out, open(f"{args.prefix}.stderr", "wb") as err:
        process = subprocess.Popen(command, cwd=args.cwd, env=env, stdout=out, stderr=err, preexec_fn=preexec)
        status = process.wait()
    wall = time.perf_counter() - t0
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    payload = {
        "argv": command,
        "cwd": str(args.cwd),
        "env": {key: env.get(key) for key in RECORDED_ENV},
        "run_as_user": args.user or pwd.getpwuid(os.getuid()).pw_name,
        "host": {"platform": platform.platform(), "cpu_count": os.cpu_count(), "python": platform.python_version()},
        "started_utc": started.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "exit_status": status,
        "wall_seconds": round(wall, 3),
        "user_cpu_seconds": round(usage.ru_utime, 3),
        "system_cpu_seconds": round(usage.ru_stime, 3),
        "peak_rss_mib": round(usage.ru_maxrss / 1024, 1),
        "secrets_present": {key: key in env for key in SECRETS},
    }
    Path(f"{args.prefix}.exec.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("exit_status", "wall_seconds", "peak_rss_mib")}))
    return status


if __name__ == "__main__":
    sys.exit(main())
