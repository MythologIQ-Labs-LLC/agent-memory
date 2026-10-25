"""Portable host-side isolation helpers for the MCP pilot harness and the alpha workflow.

Every helper either establishes the property it names or raises ``IsolationError``; none of them
silently degrades. The MCP server and bridge do not use this module.

* ``minimal_os_env``: the operating-system variables a server subprocess needs, nothing from the
  host's own environment beyond them (POSIX: a fixed ``PATH``; Windows: ``SYSTEMROOT``/``WINDIR``,
  which Python's sockets and asyncio need, a ``PATH`` of the system directories, ``PATHEXT`` and a
  private ``TEMP``/``TMP``).
* ``private_dir`` / ``private_file`` / ``verify_private``: owner-only access. POSIX uses mode bits
  and checks the owner; Windows has no meaningful mode bits, so the directory's DACL is replaced
  (inheritance removed, full control for the current user and SYSTEM only) with ``icacls`` on the
  disposable directory the harness itself created, then read back as SDDL and checked.
* ``processes_with``: process ids whose command line contains a literal fragment, or ``None`` when
  this platform offers no way to ask (callers treat ``None`` as a failed check).
* ``resolve_cli`` / ``assert_launchable``: find an executable through ``PATH``/``PATHEXT``, and
  refuse to start a ``.cmd``/``.bat`` launcher with arguments ``cmd.exe`` would reinterpret.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

IS_WINDOWS = os.name == "nt"
SYSTEM_SID = "S-1-5-18"
_SID_ALIASES = {"SY": SYSTEM_SID}
_BATCH_SUFFIXES = (".cmd", ".bat")
_CMD_METACHARACTERS = re.compile(r'["&|<>^%!\r\n]')


class IsolationError(RuntimeError):
    """A required host isolation property could not be established or verified."""


def minimal_os_env(*, platform: str | None = None, environ: dict | None = None,
                   temp_dir: str | os.PathLike | None = None) -> dict[str, str]:
    platform = platform or os.name
    environ = os.environ if environ is None else environ
    if platform != "nt":
        return {"PATH": "/usr/bin:/bin"}
    root = environ.get("SYSTEMROOT") or environ.get("SystemRoot")
    if not root:
        raise IsolationError("SYSTEMROOT is not set; a Windows Python subprocess cannot start its sockets without it")
    if temp_dir is None:
        raise IsolationError("a private TEMP directory is required on Windows")
    sep = "\\"
    return {"SYSTEMROOT": root, "WINDIR": root, "PATH": f"{root}{sep}System32;{root}",
            "PATHEXT": environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD"), "TEMP": str(temp_dir), "TMP": str(temp_dir)}


# --- Windows DACLs ------------------------------------------------------------------------------

def _aces(dacl: str) -> list[tuple[str, str, str]]:
    """(type, flags, sid) for each ACE of an SDDL DACL string."""
    out = []
    for ace in re.findall(r"\(([^)]*)\)", dacl):
        fields = ace.split(";")
        if len(fields) >= 6:
            out.append((fields[0], fields[1], _SID_ALIASES.get(fields[5], fields[5])))
    return out


def dacl_is_private(sddl: str, user_sid: str, *, directory: bool) -> bool:
    """Every allow ACE names the user or SYSTEM, at least one names the user, and a directory's
    DACL is protected (``D:P``: no inherited access from above)."""
    match = re.search(r"D:([A-Z]*)((?:\([^)]*\))*)", sddl)
    if not match:
        return False
    flags, body = match.groups()
    if directory and "P" not in flags:
        return False
    allowed = [sid for kind, _, sid in _aces(body) if kind in ("A", "OA")]
    return bool(allowed) and set(allowed) <= {user_sid, SYSTEM_SID} and user_sid in allowed


def sddl_from_icacls_save(data: bytes) -> str:
    """``icacls PATH /save FILE`` writes UTF-16 lines: the name, then its SDDL."""
    text = data.decode("utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else data.decode("utf-16-le", "replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if re.match(r"^(?:O:|G:|D:|S:)", line):
            return line
    raise IsolationError("icacls /save output carried no SDDL")


def _run(command: list[str]) -> str:
    try:
        done = subprocess.run(command, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IsolationError(f"could not run {command[0]}") from exc
    if done.returncode != 0:
        raise IsolationError(f"{command[0]} failed with exit code {done.returncode}")
    return done.stdout.decode("utf-8", "replace")


def current_user_sid() -> str:
    out = _run(["whoami", "/user", "/fo", "csv", "/nh"]).strip()
    sid = out.rsplit(",", 1)[-1].strip().strip('"')
    if not re.fullmatch(r"S-1-[0-9-]+", sid):
        raise IsolationError("could not determine the current user's SID")
    return sid


def _windows_sddl(path: Path) -> str:
    with tempfile.TemporaryDirectory(dir=path if path.is_dir() else path.parent) as temp:
        saved = Path(temp) / "acl.txt"
        _run(["icacls", str(path), "/save", str(saved)])
        return sddl_from_icacls_save(saved.read_bytes())


def _restrict_windows(path: Path) -> None:
    sid = current_user_sid()
    _run(["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F", f"*{SYSTEM_SID}:(OI)(CI)F"])


def verify_private(path: Path, *, directory: bool) -> None:
    if IS_WINDOWS:
        if not dacl_is_private(_windows_sddl(path), current_user_sid(), directory=directory):
            raise IsolationError(f"{'directory' if directory else 'file'} ACL is not limited to the current user and SYSTEM")
        return
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise IsolationError(f"{'directory' if directory else 'file'} is not private to the current user")


def private_dir(path: Path) -> Path:
    """Create (or reuse) a directory the harness owns and make it owner-only, then verify it."""
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise IsolationError("private directory is not a plain directory")
    if IS_WINDOWS:
        _restrict_windows(path)
    else:
        os.chmod(path, 0o700)
    verify_private(path, directory=True)
    return path


def private_file(path: Path, data: bytes) -> Path:
    """Write a file inside a private directory (it inherits that DACL on Windows) and verify it."""
    path.write_bytes(data)
    if not IS_WINDOWS:
        os.chmod(path, 0o600)
    verify_private(path, directory=False)
    return path


# --- processes and executables ------------------------------------------------------------------

def processes_with(fragment: str) -> list[int] | None:
    """Ids of other processes whose command line contains ``fragment`` literally; None if unknown."""
    me = os.getpid()
    if IS_WINDOWS:
        literal = fragment.replace("'", "''")
        script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
                  f"$_.CommandLine.Contains('{literal}') }} | ForEach-Object {{ $_.ProcessId }}")
        try:
            done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                  capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if done.returncode != 0:
            return None
        return sorted(int(p) for p in done.stdout.decode("utf-8", "replace").split() if p.isdigit() and int(p) != me)
    try:
        done = subprocess.run(["ps", "-A", "-o", "pid=", "-o", "args="], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    found = []
    for line in done.stdout.decode("utf-8", "replace").splitlines():
        pid, _, args = line.strip().partition(" ")
        if pid.isdigit() and int(pid) != me and fragment in args:
            found.append(int(pid))
    return sorted(found)


def resolve_cli(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise IsolationError(f"{name} was not found on PATH")
    return found


def assert_launchable(command: list[str]) -> None:
    """A batch launcher runs through cmd.exe, which reinterprets quotes, &, |, <, >, ^, % and !."""
    if Path(command[0]).suffix.lower() in _BATCH_SUFFIXES:
        for arg in command[1:]:
            if _CMD_METACHARACTERS.search(arg):
                raise IsolationError("refusing to pass cmd.exe metacharacters to a batch launcher")


def python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
