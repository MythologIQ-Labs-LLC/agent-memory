"""W2/W3 native-Windows qualification runner for the restricted Stage A/B alpha (stdlib only).

Run only after ``preflight.py`` wrote ``preflight.json`` with decision GO into the same --dev-dir:

    py -3.12 integrations\\agent-memory-mcp\\windows\\qualify.py --dev-dir D:\\am-win-dev --python 3.11 --python 3.12

For each requested Python it creates ``<dev-dir>\\venv-<version>`` (refusing an existing one),
installs only this clone and ``mcp==2.3.0`` into it, and runs, with every ``AGENT_MEMORY_*``
variable removed and a private TEMP inside --dev-dir:

1. the MCP suites (unit, real stdio MCP, pilot harness, hostenv, and the native NTFS negatives in
   ``test_windows_native.py``: any skip there is a missing capability and is NOT a pass);
2. the public-facade lifecycle tests;
3. the Stage A/B alpha workflow (``alpha_workflow.py``);
4. the 16-session real-agent pilot (``pilot/agent_pilot.py``), unless --no-pilot.

Afterwards it re-checks the preflight baseline: the base interpreters' packages, the user and
machine environment variables and the Claude Code configuration files must be unchanged. Evidence
goes to ``reports/validation/mcp-windows-qualification/py<version>-<head>/`` with local paths
replaced by labels. Nothing is committed: review the evidence, then commit it with ``[skip ci]``.
A Python whose every step passes is GO; anything else is NO-GO with the failing step named.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MCP_DIR = HERE.parent
REPO = MCP_DIR.parents[1]
EVIDENCE = REPO / "reports" / "validation" / "mcp-windows-qualification"
NATIVE_MODULE = "test_windows_native"


def parse_unittest(text: str) -> dict:
    """Totals from ``unittest -v`` output, with skipped tests listed per module."""
    ran = re.search(r"^Ran (\d+) tests?", text, re.MULTILINE)
    status = re.search(r"^(OK|FAILED)(?: \(([^)]*)\))?\s*$", text, re.MULTILINE)
    counts = dict(re.findall(r"(\w[\w ]*?)=(\d+)", status.group(2) or "")) if status else {}
    skipped = re.findall(r"^(\w+) \(([\w.]+)\)[^\n]*? \.\.\. skipped '([^']*)'", text, re.MULTILINE)
    return {"ran": int(ran.group(1)) if ran else 0, "ok": bool(status and status.group(1) == "OK"),
            "failures": int(counts.get("failures", 0)), "errors": int(counts.get("errors", 0)),
            "skipped": [{"test": t, "where": w, "reason": r} for t, w, r in skipped],
            "expected_failures": int(counts.get("expected failures", 0))}


def native_negatives_passed(result: dict) -> bool:
    return result["ok"] and not [s for s in result["skipped"] if NATIVE_MODULE in s["where"]]


def redact_text(text: str, labels: list[tuple[str, str]]) -> str:
    for path, label in labels:
        for form in {path, path.replace("\\", "/")}:
            if form:
                text = re.sub(re.escape(form), label, text, flags=re.IGNORECASE)
    return text


def run(command: list[str], *, env: dict, cwd: Path, log: Path, labels, timeout: int = 7200) -> tuple[int, str]:
    try:
        done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
        code, text = done.returncode, (done.stdout + done.stderr).decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        code, text = -1, f"{type(exc).__name__}: {exc}"
    log.write_text(redact_text(f"$ {' '.join(Path(c).name if i == 0 else c for i, c in enumerate(command))}\n{text}\nexit={code}\n",
                               labels), encoding="utf-8")
    return code, text


def child_env(temp: Path, config_dir: str | None) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("AGENT_MEMORY")}
    env.update({"TEMP": str(temp), "TMP": str(temp), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dev-dir", type=Path, required=True)
    parser.add_argument("--python", action="append", required=True, choices=("3.11", "3.12"))
    parser.add_argument("--no-pilot", action="store_true")
    options = parser.parse_args()
    if os.name != "nt":
        print(json.dumps({"decision": "NO-GO", "reason": "not native Windows: this runner does not simulate Windows"}))
        return 1
    sys.path.insert(0, str(MCP_DIR))
    import hostenv
    import preflight as pf

    dev = options.dev_dir
    try:
        pre = json.loads((dev / "preflight.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(json.dumps({"decision": "NO-GO", "reason": "no readable preflight.json in --dev-dir: run preflight.py first"}))
        return 1
    if pre.get("decision") != "GO":
        print(json.dumps({"decision": "NO-GO", "reason": "preflight decision is not GO"}))
        return 1
    base = pre["baseline"]
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    labels = [(str(dev), "<DEV>"), (str(REPO), "<REPO>"), (str(Path.home()), "<HOME>"),
              (os.environ.get("USERNAME", "") and f"\\{os.environ['USERNAME']}\\", "\\<USER>\\")]
    results = {}
    for version in options.python:
        exe = base["pythons"].get(version)
        steps: dict[str, dict] = {}
        out = EVIDENCE / f"py{version}-{head[:8]}"
        out.mkdir(parents=True, exist_ok=False)
        venv = dev / f"venv-{version}"
        temp = hostenv.private_dir(dev / f"tmp-{version}")
        env = child_env(temp, base.get("claude_config_dir"))
        if not exe or venv.exists():
            steps["venv"] = {"passed": False, "detail": "interpreter missing" if not exe else "venv already exists"}
        else:
            code, _ = run([exe, "-m", "venv", str(venv)], env=env, cwd=dev, log=out / "venv.log", labels=labels)
            py = str(venv / "Scripts" / "python.exe")
            code2, _ = run([py, "-m", "pip", "install", "-e", str(REPO), "mcp==2.3.0"], env=env, cwd=REPO,
                           log=out / "install.log", labels=labels)
            steps["venv"] = {"passed": code == 0 and code2 == 0}
            if steps["venv"]["passed"]:
                run([py, "-m", "pip", "freeze", "--all"], env=env, cwd=REPO, log=out / "pip-freeze.log", labels=labels)
                code, text = run([py, "-m", "unittest", "discover", "-s", "integrations/agent-memory-mcp/tests",
                                  "-p", "test_*.py", "-v"], env=env, cwd=REPO, log=out / "mcp-suites.log", labels=labels)
                suites = parse_unittest(text)
                steps["mcp_suites"] = {"passed": code == 0 and suites["ok"], **suites}
                steps["native_security_negatives"] = {"passed": native_negatives_passed(suites),
                                                      "unavailable_capabilities": [s for s in suites["skipped"] if NATIVE_MODULE in s["where"]]}
                code, text = run([py, "-m", "unittest", "discover", "-s", "reference/tests", "-t", "reference",
                                  "-p", "test_developer_facade.py", "-v"], env=env, cwd=REPO, log=out / "facade.log", labels=labels)
                steps["facade"] = {"passed": code == 0 and parse_unittest(text)["ok"], **parse_unittest(text)}
                code, text = run([py, "reports/validation/mcp-internal-alpha/alpha_workflow.py", str(REPO), str(out)],
                                 env=env, cwd=REPO, log=out / "alpha-workflow.log", labels=labels)
                steps["alpha_workflow"] = {"passed": code == 0, "summary": (re.findall(r"\d+/\d+ checks passed", text) or [None])[-1]}
                if not options.no_pilot:
                    code, text = run([py, "integrations/agent-memory-mcp/pilot/agent_pilot.py", "--run-dir",
                                      str(dev / f"pilot-run-{version}"), "--out", str(out / "pilot")],
                                     env=env, cwd=REPO, log=out / "pilot.log", labels=labels)
                    steps["real_agent_pilot"] = {"passed": code == 0}
        # Baseline re-checks: nothing outside --dev-dir changed.
        now_pip = {}
        for v, path in sorted(base["pythons"].items()):
            c, frozen = pf.run([path, "-m", "pip", "freeze", "--all"])
            now_pip[v] = hashlib.sha256(frozen.encode("utf-8")).hexdigest() if c == 0 else None
        config_dir = Path(base["claude_config_dir"]) if base.get("claude_config_dir") else None
        steps["base_interpreters_unchanged"] = {"passed": now_pip == base["pip_freeze_sha256"]}
        steps["user_and_machine_environment_unchanged"] = {
            "passed": pf.environment_digest(pf.registry_environment()) == base["registry_environment_sha256"]}
        now_cfg = pf.config_snapshot(config_dir)
        # A legacy preflight without both baselines is not sufficient evidence.
        cfg_baseline = base.get("claude_config_sha256", {})
        steps["default_claude_config_unchanged"] = {
            "passed": isinstance(cfg_baseline, dict) and
                      "default" in cfg_baseline and now_cfg["default"] == cfg_baseline["default"]
        }
        # The isolated directory is inside --dev-dir and may legitimately change
        # during an authenticated pilot. Report changes, but do not fail admission.
        steps["isolated_claude_config_contained"] = {
            "passed": not config_dir or (
                "isolated" in cfg_baseline and
                pf.is_strict_child(config_dir, dev) and
                not pf.overlaps(config_dir, Path.home() / ".claude")
            ),
            "changed": bool(config_dir and now_cfg["isolated"] != cfg_baseline.get("isolated")),
        }
        decision = "GO" if steps and all(s["passed"] for s in steps.values()) else "NO-GO"
        results[version] = {"decision": decision, "failed_steps": [k for k, s in steps.items() if not s["passed"]]}
        (out / "summary.json").write_text(redact_text(json.dumps({
            "schema": "agent-memory-windows-qualification/0.1.0", "head": head, "python": version, "decision": decision,
            "preflight": {"decision": pre["decision"], "checks": [{k: c[k] for k in ("n", "property", "result")} for c in pre["checks"]]},
            "steps": steps}, indent=1), labels) + "\n", encoding="utf-8")
        shutil.copyfile(dev / "preflight.json", out / "preflight.raw.json")
        (out / "preflight.json").write_text(redact_text((out / "preflight.raw.json").read_text(encoding="utf-8"), labels), encoding="utf-8")
        (out / "preflight.raw.json").unlink()
    print(json.dumps(results, indent=1))
    return 0 if all(r["decision"] == "GO" for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
