#!/usr/bin/env python3
"""Execute one frozen-AMB run locally and record its evidence bundle.

This wraps ``reference/run_amb_external.py`` as a child process; it never scores, edits or
summarises a result itself. The bundle records what is needed to reproduce and audit the
run: both revisions, the interpreter and installed distributions, the exact command, exit
status, wall time and peak RSS of the run process, stdout/stderr verbatim, the git blobs of
the AMB files that load data and score, the dataset fixture digests, and a sha256 of every
file AMB wrote. Inference credentials are removed from the child environment so a
retrieval run cannot reach a paid API.

Example::

    python scripts/run_amb_local_evidence.py \\
      --amb-root /tmp/agent-memory-benchmark --python .venv/bin/python \\
      --evidence-dir reports/benchmarks/amb-local/<run-id> \\
      -- run --dataset precisionmembench --split single-turn --memory agent-memory --mode retrieval
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "reference" / "run_amb_external.py"
CREDENTIAL_ENV = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "SUPERMEMORY_API_KEY",
)
AMB_SCORING_FILES = (
    "src/memory_bench/cli.py",
    "src/memory_bench/runner.py",
    "src/memory_bench/modes/retrieval.py",
    "src/memory_bench/dataset/precisionmembench.py",
    "src/memory_bench/memory/base.py",
    "src/memory_bench/memory/bm25.py",
    "src/memory_bench/utils.py",
)
BRIDGE_FILES = (
    "reference/amb_agent_memory_bridge.py",
    "reference/amb_retrieval_no_llm.py",
    "reference/run_amb_external.py",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _option(amb_args: list[str], name: str) -> str | None:
    for index, arg in enumerate(amb_args):
        if arg == name and index + 1 < len(amb_args):
            return amb_args[index + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return None


def _environment(python: str) -> dict[str, object]:
    probe = (
        "import json, platform, sys, importlib.metadata as m;"
        "print(json.dumps({'python': sys.version, 'implementation': platform.python_implementation(),"
        "'distributions': sorted(f\"{d.metadata['Name']}=={d.version}\" for d in m.distributions())}))"
    )
    payload = json.loads(subprocess.run([python, "-I", "-c", probe], check=True, capture_output=True, text=True).stdout)
    payload["platform"] = platform.platform()
    payload["machine"] = platform.machine()
    payload["cpu_count"] = os.cpu_count()
    try:
        meminfo = Path("/proc/meminfo").read_text().splitlines()[0]
        payload["memtotal"] = meminfo.split(":", 1)[1].strip()
    except OSError:
        payload["memtotal"] = None
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--amb-root", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable, help="interpreter of the harness environment")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--runner-flag", action="append", default=[], help="extra flag for run_amb_external.py")
    parser.add_argument("--set-env", action="append", default=[], help="KEY=VALUE for the child (recorded by key only)")
    parser.add_argument("amb_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.amb_args and args.amb_args[0] == "--":
        args.amb_args = args.amb_args[1:]
    if not args.amb_args:
        parser.error("AMB CLI arguments are required after '--'")
    if _option(args.amb_args, "--output-dir") is not None:
        parser.error("--output-dir is owned by this script (it writes under --evidence-dir)")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    amb_root = args.amb_root.resolve()
    evidence = args.evidence_dir.resolve()
    if evidence.exists():
        raise SystemExit(f"evidence dir already exists, refusing to overwrite: {evidence}")
    outputs = evidence / "amb-outputs"
    outputs.mkdir(parents=True)

    env = {key: value for key, value in os.environ.items() if key not in CREDENTIAL_ENV}
    for item in args.set_env:
        key, _, value = item.partition("=")
        env[key] = value
    command = [args.python, str(RUNNER), "--amb-root", str(amb_root), *args.runner_flag, "--", *args.amb_args, "--output-dir", str(outputs)]

    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    with (evidence / "stdout.txt").open("wb") as out, (evidence / "stderr.txt").open("wb") as err:
        process = subprocess.Popen(command, cwd=REPO_ROOT, env=env, stdout=out, stderr=err)
        _, status, usage = os.wait4(process.pid, 0)
    wall_s = time.perf_counter() - t0
    exit_code = os.waitstatus_to_exitcode(status)

    dataset = _option(args.amb_args, "--dataset")
    fixtures = {}
    fixture_dir = amb_root / ".datasets" / (dataset or "")
    if dataset and fixture_dir.is_dir():
        fixtures = {path.name: _sha256(path) for path in sorted(fixture_dir.iterdir()) if path.is_file()}

    written = sorted(path for path in outputs.rglob("*") if path.is_file())
    identity = {
        "schema": "agent-memory-amb-local-execution/1",
        "started_utc": started.isoformat(timespec="seconds"),
        "command": [str(part) for part in command],
        "child_env_overrides": sorted(item.partition("=")[0] for item in args.set_env),
        "credentials_removed": [key for key in CREDENTIAL_ENV if key in os.environ] or [],
        "credentials_present_in_child": [key for key in CREDENTIAL_ENV if key in env],
        "exit_code": exit_code,
        "wall_time_s": round(wall_s, 3),
        "peak_rss_kib": usage.ru_maxrss,
        "user_cpu_s": round(usage.ru_utime, 3),
        "system_cpu_s": round(usage.ru_stime, 3),
        "agent_memory": {
            "revision": _git(REPO_ROOT, "rev-parse", "HEAD"),
            "worktree_dirty_paths": [line for line in _git(REPO_ROOT, "status", "--porcelain").splitlines() if line],
            "bridge_blobs": {path: _git(REPO_ROOT, "hash-object", path) for path in BRIDGE_FILES},
        },
        "amb": {
            "repository": "vectorize-io/agent-memory-benchmark",
            "revision": _git(amb_root, "rev-parse", "HEAD"),
            "worktree_dirty_paths": [line for line in _git(amb_root, "status", "--porcelain", "--untracked-files=no").splitlines() if line],
            "scoring_blobs": {path: _git(amb_root, "hash-object", path) for path in AMB_SCORING_FILES},
            "uv_lock_sha256": _sha256(amb_root / "uv.lock"),
        },
        "dataset_fixtures_sha256": fixtures,
        "tiktoken_cache_dir": env.get("TIKTOKEN_CACHE_DIR"),
        "environment": _environment(args.python),
        "outputs_sha256": {str(path.relative_to(evidence)): _sha256(path) for path in written},
    }
    (evidence / "execution-identity.json").write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: identity[key] for key in ("exit_code", "wall_time_s", "peak_rss_kib")}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
