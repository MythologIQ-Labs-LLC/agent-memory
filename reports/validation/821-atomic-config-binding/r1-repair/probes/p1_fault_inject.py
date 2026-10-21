"""In-process fault injection at every step of GenerationWitness.record (repaired tree).

For each fault: the published witness must be either the old complete record or the new complete
record; no temporary of ours may remain (except where noted); no fd may leak; the exception type
must be what _record_witness expects (OSError) unless the fault is a BaseException.
"""
import builtins
import errno
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, sys.argv[1])
from agentmem_ref.runtime import sqlite_runtime as sr  # noqa: E402

W = sr.GenerationWitness


def fds():
    return set(os.listdir("/proc/self/fd"))


def state(root):
    p = root / "generation-witness.json"
    raw = p.read_bytes() if p.exists() else None
    temps = sorted(x.name for x in root.iterdir() if x.name != "generation-witness.json")
    return raw, temps


class Boom(OSError):
    pass


def run(name, patcher, expect_new=False):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        w = W(root)
        w.record(1, "sha256:old")
        old = (root / "generation-witness.json").read_bytes()
        before = fds()
        exc = None
        with patcher(root):
            try:
                w.record(2, "sha256:new")
            except BaseException as e:  # noqa: BLE001
                exc = e
        after = fds()
        raw, temps = state(root)
        try:
            parsed = W(root).read()
        except Exception as e:  # noqa: BLE001
            parsed = f"REFUSED {e}"
        which = "old" if raw == old else ("new" if parsed == (2, "sha256:new") else f"OTHER {raw!r}")
        leak = sorted(after - before)
        print(f"{name:38s} exc={type(exc).__name__ if exc else None:18s} witness={which:4s} "
              f"temps={temps} fd_leak={leak}")


def patch_attr(obj, attr, fn):
    def factory(root):
        return mock.patch.object(obj, attr, fn)
    return factory


real_open = os.open
real_fdopen = os.fdopen
real_fsync = os.fsync
real_replace = os.replace


def os_open_fail(path, flags, *a, **k):
    if ".tmp" in os.fspath(path):
        raise OSError(errno.EDQUOT, "injected EDQUOT")
    return real_open(path, flags, *a, **k)


def os_open_eexist(path, flags, *a, **k):
    if ".tmp" in os.fspath(path):
        raise FileExistsError(errno.EEXIST, "always taken")
    return real_open(path, flags, *a, **k)


def fdopen_fail(fd, *a, **k):
    raise MemoryError("injected in fdopen")


def fdopen_fail_os(fd, *a, **k):
    raise OSError(errno.EIO, "injected EIO in fdopen")


class FailingWrite(io.RawIOBase):
    pass


def fdopen_bad_write(fd, *a, **k):
    h = real_fdopen(fd, *a, **k)

    class Wrap:
        def __enter__(s):
            return s

        def __exit__(s, *e):
            h.close()

        def write(s, b):
            raise OSError(errno.ENOSPC, "injected ENOSPC on write")

        def flush(s):
            h.flush()

        def fileno(s):
            return h.fileno()

    return Wrap()


def fsync_first_fails():
    calls = {"n": 0}

    def f(fd):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError(errno.EIO, "injected EIO on file fsync")
        return real_fsync(fd)
    return f


def fsync_dir_fails():
    calls = {"n": 0}

    def f(fd):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError(errno.EINVAL, "injected EINVAL on dir fsync")
        return real_fsync(fd)
    return f


def replace_fail(src, dst, *a, **k):
    raise OSError(errno.ENOSPC, "injected rename failure")


def replace_kbi(src, dst, *a, **k):
    raise KeyboardInterrupt()


def replace_then_raise(src, dst, *a, **k):
    real_replace(src, dst, *a, **k)
    raise OSError(errno.ETIMEDOUT, "rename done on server, client saw timeout")


def replace_then_kbi(src, dst, *a, **k):
    real_replace(src, dst, *a, **k)
    raise KeyboardInterrupt()


run("os.open EDQUOT", patch_attr(sr.os, "open", os_open_fail))
run("os.open always EEXIST (8 retries)", patch_attr(sr.os, "open", os_open_eexist))
run("os.fdopen MemoryError", patch_attr(sr.os, "fdopen", fdopen_fail))
run("os.fdopen OSError", patch_attr(sr.os, "fdopen", fdopen_fail_os))
run("write ENOSPC", patch_attr(sr.os, "fdopen", fdopen_bad_write))
run("file fsync EIO", lambda r: mock.patch.object(sr.os, "fsync", fsync_first_fails()))
run("os.replace OSError", patch_attr(sr.os, "replace", replace_fail))
run("os.replace KeyboardInterrupt", patch_attr(sr.os, "replace", replace_kbi))
run("os.replace done then OSError (NFS)", patch_attr(sr.os, "replace", replace_then_raise))
run("os.replace done then KeyboardInterrupt", patch_attr(sr.os, "replace", replace_then_kbi))
run("dir fsync EINVAL", lambda r: mock.patch.object(sr.os, "fsync", fsync_dir_fails()))

# KeyboardInterrupt raised by the fd-returning helper's caller before the try (window probe):
def kbi_after_exclusive(root):
    real = W._exclusive_temporary

    def f(self):
        real(self)
        raise KeyboardInterrupt()
    return mock.patch.object(W, "_exclusive_temporary", f)


run("KBI between O_EXCL open and try", kbi_after_exclusive)

# Mode check vs open("wb") under several umasks
for um in (0o022, 0o077, 0o027, 0o002, 0o000):
    with tempfile.TemporaryDirectory() as d:
        prev = os.umask(um)
        try:
            W(Path(d)).record(1, "x")
            with open(Path(d) / "ref", "wb"):
                pass
        finally:
            os.umask(prev)
        a = (Path(d) / "generation-witness.json").stat().st_mode & 0o7777
        b = (Path(d) / "ref").stat().st_mode & 0o7777
        print(f"umask {um:04o}: witness {a:04o} open('wb') {b:04o} {'same' if a == b else 'DIFFERENT'}")

# Pre-planted symlink at the next temporary name: O_EXCL must refuse to follow it
with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
    root = Path(d)
    target = Path(outside) / "victim"
    target.write_bytes(b"victim content")
    toks = iter(["a" * 16, "b" * 16])
    link = root / f".generation-witness.json.{os.getpid()}.{'a' * 16}.tmp"
    os.symlink(target, link)
    dangling = root / f".generation-witness.json.{os.getpid()}.{'c' * 16}.tmp"
    with mock.patch.object(sr.secrets, "token_hex", lambda n: next(toks)):
        W(root).record(3, "y")
    print("symlink pre-planted: victim", target.read_bytes(), "witness", W(root).read(),
          "link still symlink", link.is_symlink())
