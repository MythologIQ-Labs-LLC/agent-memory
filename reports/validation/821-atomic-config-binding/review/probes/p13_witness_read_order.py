"""P13: deterministic version of the P12 race. A second handle commits one generation (and writes
its witness) right after the reader's base recovery returns and before the reader checks the
witness and the binding row. Nothing was rolled back; what does the reader say?"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
from agentmem_ref.runtime import sqlite_runtime as R  # noqa: E402


def main():
    root = C.tmp() / "s"
    writer = C.open_mem(root, actor="agent:w")
    writer.remember("memory:x", "seed")
    orig = R.SQLiteRestartSafeRuntime.recover.__func__
    fired = {"n": 0}

    def recover(cls, *a, **k):
        base = orig(cls, *a, **k)
        if fired["n"] == 0:
            fired["n"] = 1
            writer.remember("memory:y", "committed by another handle in between")
        return base

    with mock.patch.object(R.SQLiteRestartSafeRuntime, "recover", classmethod(recover)):
        try:
            C.open_mem(root, actor="agent:r").close()
            print("reader: OK")
        except Exception as e:  # noqa
            print(f"reader: {type(e).__name__}: {e}")
    writer.close()
    print("reopen afterwards:", C.try_open(root))


if __name__ == "__main__":
    main()
