"""W1 native-Windows preflight for the restricted Stage A/B alpha (stdlib only).

Run from a dedicated clone, with any installed Python 3.11+, in a normal (non-elevated) shell:

    py -3.12 integrations\\agent-memory-mcp\\windows\\preflight.py --dev-dir D:\\am-win-dev [--stable-path PATH ...]
        [--claude-config-dir D:\\am-win-dev\\claude-config]

It changes nothing outside --dev-dir. Inside --dev-dir it creates only a disposable
``preflight-*`` directory (removed again) to prove that a harmless NTFS junction is refused, and it
writes ``preflight.json``: one entry per required property, PASS or FAIL with its evidence, the
baseline the qualification runner later re-checks (base interpreters' packages, the user and
machine environment variables, the Claude Code configuration files), and GO or NO-GO. Any FAIL is
NO-GO: stop before provisioning anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MCP_DIR = HERE.parent
REPO = MCP_DIR.parents[1]
REQUIRED_PYTHONS = ("3.11", "3.12")
STORE_HINTS = ("agent-memory", "agent_memory", "agentmem")


def run(command: list[str], timeout: int = 120, env: dict | None = None, stdin: str | None = None) -> tuple[int, str]:
    try:
        done = subprocess.run(command, capture_output=True, timeout=timeout, env=env,
                              input=stdin.encode("utf-8") if stdin is not None else None,
                              stdin=None if stdin is not None else subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    return done.returncode, (done.stdout + done.stderr).decode("utf-8", "replace")


def sha256_or_none(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def parse_py_list(text: str) -> dict[str, str]:
    """``py -0p`` lines such as `` -V:3.12 *        C:\\Python312\\python.exe`` -> {"3.12": path}."""
    found = {}
    for line in text.splitlines():
        match = re.match(r"\s*-V:(\d+\.\d+)(?:-\d+)?\s+\*?\s*(.+?python(?:w)?\.exe)\s*$", line, re.IGNORECASE)
        if match:
            found.setdefault(match.group(1), match.group(2).strip())
    return found


def registry_environment() -> dict[str, dict[str, str]]:
    """User and machine environment variables, read-only."""
    import winreg
    out = {}
    for label, hive, key in (("user", winreg.HKEY_CURRENT_USER, r"Environment"),
                             ("machine", winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
        values = {}
        try:
            with winreg.OpenKey(hive, key) as handle:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(handle, i)
                    except OSError:
                        break
                    values[name] = str(value)
                    i += 1
        except OSError:
            pass
        out[label] = values
    return out


def environment_digest(env: dict[str, dict[str, str]]) -> str:
    return hashlib.sha256(json.dumps(env, sort_keys=True).encode("utf-8")).hexdigest()


def claude_config_files(config_dir: Path | None) -> list[Path]:
    home = Path.home()
    if config_dir:
        return [config_dir / ".claude.json", config_dir / "settings.json"]
    return [home / ".claude.json", home / ".claude" / "settings.json", home / ".claude" / "settings.local.json"]


def overlaps(a: Path, b: Path) -> bool:
    a, b = Path(os.path.normcase(os.path.abspath(a))), Path(os.path.normcase(os.path.abspath(b)))
    return a == b or a in b.parents or b in a.parents


def is_strict_child(child: Path, parent: Path) -> bool:
    child_path = Path(os.path.normcase(os.path.abspath(child)))
    parent_path = Path(os.path.normcase(os.path.abspath(parent)))
    return child_path != parent_path and parent_path in child_path.parents


def elevated() -> bool | None:
    """Return None if the integrity level cannot be verified (fail closed)."""
    code, out = run(["whoami", "/groups"])
    if code != 0:
        return None
    # Mandatory integrity SIDs: medium 8192, high 12288, system 16384.
    levels = [int(x) for x in re.findall(r"S-1-16-(\\d+)", out)]
    if not levels:
        return None
    return max(levels) >= 12288


def config_snapshot(config_dir: Path | None) -> dict[str, dict[str, str | None]]:
    """Always baseline the default Claude files, even with isolated config."""
    return {
        "default": {str(f): sha256_or_none(f) for f in claude_config_files(None)},
        "isolated": {str(f): sha256_or_none(f) for f in claude_config_files(config_dir)} if config_dir else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dev-dir", type=Path, required=True)
    parser.add_argument("--stable-path", type=Path, action="append", default=[],
                        help="a stable Agent Memory installation or data path that must not overlap")
    parser.add_argument("--claude-config-dir", type=Path,
                        help="an isolated CLAUDE_CONFIG_DIR for the pilot agent (recommended)")
    options = parser.parse_args()
    checks: list[dict] = []

    def check(n: int, name: str, ok: bool, evidence) -> None:
        checks.append({"n": n, "property": name, "result": "PASS" if ok else "FAIL", "evidence": evidence})

    if os.name != "nt":
        check(1, "native Windows", False, f"os.name={os.name}: a Linux or macOS run is not Windows qualification")
        report = {"decision": "NO-GO", "checks": checks}
        print(json.dumps(report, indent=1))
        return 1

    sys.path.insert(0, str(MCP_DIR))
    import bridge
    import hostenv

    dev = options.dev_dir
    # 1. Windows version and NTFS
    import ctypes
    fs = ctypes.create_unicode_buffer(64)
    drive = dev.drive if dev.drive else Path.cwd().drive
    vol_ok = bool(ctypes.windll.kernel32.GetVolumeInformationW(drive + "\\", None, 0, None, None, None, fs, 64))
    check(1, "Windows version and NTFS", vol_ok and fs.value == "NTFS" and bridge._drive_type(drive) == 3,
          {"windows": platform.platform(), "build": sys.getwindowsversion().build, "dev_drive_filesystem": fs.value,
           "dev_drive_type": bridge._drive_type(drive)})
    # 2. Python 3.11 and 3.12
    code, listing = run(["py", "-0p"])
    pythons = parse_py_list(listing) if code == 0 else {}
    check(2, "Python 3.11 and 3.12 available", all(v in pythons for v in REQUIRED_PYTHONS),
          {"py_launcher": code == 0, "found": sorted(pythons)})
    # 3. Existing installations are not modified: record their package baseline (re-checked later)
    baseline = {}
    for version, exe in sorted(pythons.items()):
        c, frozen = run([exe, "-m", "pip", "freeze", "--all"])
        baseline[version] = hashlib.sha256(frozen.encode("utf-8")).hexdigest() if c == 0 else None
    check(3, "base interpreters baselined (no global installs will be made)",
          all(baseline.get(v) for v in REQUIRED_PYTHONS), {"pip_freeze_sha256": baseline})
    # 4. Isolated development directory
    dev_problems = []
    if not dev.is_absolute():
        dev_problems.append("not absolute")
    elif bridge._windows_root_problem(__import__("pathlib").PureWindowsPath(str(dev))):
        dev_problems.append(bridge._windows_root_problem(__import__("pathlib").PureWindowsPath(str(dev))))
    if "onedrive" in str(dev).lower() or (os.environ.get("OneDrive") and overlaps(dev, Path(os.environ["OneDrive"]))):
        dev_problems.append("inside a OneDrive-synchronised folder")
    try:
        if any(bridge._redirected(c) for c in (dev, *dev.parents)):
            dev_problems.append("an existing component is a junction, symlink or reparse point")
    except OSError as exc:
        dev_problems.append(f"a component cannot be inspected: {exc}")
    if dev.exists() and any(p.name not in ("agent-memory", "preflight.json", "claude-config") for p in dev.iterdir()):
        dev_problems.append("not empty (only the clone, preflight.json and claude-config may be present)")
    if os.path.normcase(os.path.abspath(REPO.parent)) != os.path.normcase(os.path.abspath(dev)):
        dev_problems.append("the clone must be directly inside --dev-dir")
    if options.claude_config_dir is not None:
        cfg = options.claude_config_dir
        if not cfg.is_absolute() or not is_strict_child(cfg, dev):
            dev_problems.append("isolated Claude config must be a descendant of the development directory")
        if overlaps(cfg, Path.home() / ".claude") or overlaps(cfg, Path.home() / ".claude.json"):
            dev_problems.append("isolated Claude config overlaps the default Claude installation")
    check(4, "isolated development directory", not dev_problems, {"problems": dev_problems})
    # 5. Separate from any stable installation or data
    stable_candidates = [Path(os.environ.get("LOCALAPPDATA", "")) / "agent-memory", Path.home() / ".agent-memory",
                         Path.home() / ".cache" / "agent-memory", *options.stable_path]
    clashes = [str(p) for p in stable_candidates if str(p) not in ("", ".") and overlaps(dev, p)]
    check(5, "separate from stable Agent Memory installations and data", not clashes,
          {"checked": len(stable_candidates), "overlapping": clashes})
    # 6. No production memory store referenced
    registry = registry_environment()
    referenced = sorted({f"{scope}:{name}" for scope, values in registry.items() for name in values
                         if name.upper().startswith("AGENT_MEMORY")} |
                        {f"process:{name}" for name in os.environ if name.upper().startswith("AGENT_MEMORY")})
    check(6, "no Agent Memory store referenced by any environment", not referenced, {"variables": referenced})
    # 7. Local user and directory permissions
    is_elevated = elevated()
    acl_ok, acl_detail = False, None
    probe = dev / "preflight-acl"
    try:
        hostenv.private_dir(probe)
        acl_ok = True
    except Exception as exc:  # noqa: BLE001 - recorded as the evidence of the failure
        acl_detail = f"{type(exc).__name__}: {exc}"
    finally:
        run(["cmd", "/c", "rmdir", "/s", "/q", str(probe)])
    check(7, "non-elevated user; private ACLs can be set and verified in the dev dir",
          is_elevated is False and acl_ok, {"elevated": is_elevated, "integrity_level_verified": is_elevated is not None,
                                         "user_sid_known": bool(acl_ok), "acl_error": acl_detail})
    # 8. Junction redirection cannot escape the test boundary
    box = dev / "preflight-junction"
    escape_refused, written_behind = False, None
    try:
        (box / "target").mkdir(parents=True, exist_ok=True)
        code, _ = run(["cmd", "/c", "mklink", "/J", str(box / "jn"), str(box / "target")])
        if code == 0:
            os.environ["AGENT_MEMORY_MCP_ROOT"] = str(box / "jn" / "store")
            for name, value in (("TENANT", "tenant:preflight"), ("ACTOR", "agent:preflight"), ("SCOPE", "project:preflight")):
                os.environ[f"AGENT_MEMORY_MCP_{name}"] = value
            try:
                bridge.HostConfig.from_environment()
            except ValueError:
                escape_refused = True
            finally:
                for name in ("ROOT", "TENANT", "ACTOR", "SCOPE"):
                    os.environ.pop(f"AGENT_MEMORY_MCP_{name}", None)
            written_behind = any((box / "target").iterdir())
    finally:
        run(["cmd", "/c", "rmdir", "/s", "/q", str(box)])
    check(8, "junction redirection is refused before anything is written", escape_refused and written_behind is False,
          {"refused": escape_refused, "written_behind_junction": written_behind})
    # 9. Environment changes stay in child processes (re-checked by the runner)
    check(9, "environment confined to child processes (baseline recorded)", True,
          {"registry_environment_sha256": environment_digest(registry),
           "note": "the runner compares this digest after qualification; preflight writes no environment"})
    # 10. Claude Code CLI runs without modifying another installation's configuration
    cli = shutil.which("claude")
    config_dir = options.claude_config_dir
    before = config_snapshot(config_dir)
    env = dict(os.environ)
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    version = run([cli, "--version"], env=env)[1].strip() if cli else None
    probe_code, probe_out = (run([cli, "-p", "--tools", "", "--strict-mcp-config", "--no-session-persistence",
                                 "--setting-sources", "project", "--output-format", "json"], env=env, timeout=300,
                                stdin="Reply with the single word: ready")
                             if cli else (-1, "claude not found"))
    after = config_snapshot(config_dir)
    default_untouched = before["default"] == after["default"]
    check(10, "Claude Code CLI available and another installation's configuration untouched",
          bool(cli) and probe_code == 0 and default_untouched,
          {"cli_found": bool(cli), "version": version, "probe_exit": probe_code,
           "isolated_config_dir": bool(config_dir), "default_config_changed": not default_untouched,
           "advice": None if default_untouched else "use --claude-config-dir and log in there once"})

    decision = "GO" if all(c["result"] == "PASS" for c in checks) else "NO-GO"
    report = {"schema": "agent-memory-windows-preflight/0.1.0", "decision": decision,
              "python_running_preflight": platform.python_version(), "checks": checks,
              "baseline": {"pip_freeze_sha256": baseline, "registry_environment_sha256": environment_digest(registry),
                           "claude_config_sha256": after, "pythons": pythons, "claude_config_dir": str(config_dir) if config_dir else None}}
    dev.mkdir(parents=True, exist_ok=True)
    (dev / "preflight.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "failed": [c["property"] for c in checks if c["result"] == "FAIL"]}, indent=1))
    return 0 if decision == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
