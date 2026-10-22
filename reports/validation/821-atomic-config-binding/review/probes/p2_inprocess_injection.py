"""P2: in-process exception / KeyboardInterrupt at every boundary of the publication path.

Pre-COMMIT points: durable rows must be byte-identical, in-memory governance restored (or, for a
bare checkpoint(), the pending in-memory change still pending), the handle keeps working, and a
reopen recovers row == state with no lost committed or pending seam change.
Post-COMMIT points: the generation stays committed and bound; reopen recovers it.
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
from agentmem_ref.runtime import sqlite_runtime as R, configured_restart as CR, restart_runtime as RR  # noqa: E402
from agentmem_ref.state import sqlite_substrate as S  # noqa: E402


def gov(memory):
    return json.dumps(memory.runtime.adapter.export_checkpoint_state(), sort_keys=True, default=str)


def patch_for(point, exc):
    def raiser(*a, **k):
        raise exc

    def after(cls, name):
        orig = getattr(cls, name)

        def hook(*a, **k):
            orig(*a, **k)
            raise exc
        return mock.patch.object(cls, name, hook)

    if point == "after_state":
        return after(S.SQLiteTemporalGraph, "write_runtime_state"), True
    if point == "after_journal":
        return after(S.SQLiteTemporalGraph, "append_runtime_journal"), True
    if point == "binder_entry":
        if not hasattr(R, "SQLiteConfigBindingStore"):
            return None, True
        return mock.patch.object(R.SQLiteConfigBindingStore, "publish", raiser), True
    if point == "after_row":
        if not hasattr(S.SQLiteTemporalGraph, "write_runtime_configuration_binding"):
            return None, True
        return after(S.SQLiteTemporalGraph, "write_runtime_configuration_binding"), True
    if point == "before_commit":
        return mock.patch.object(RR.CheckpointableGovernedMemoryAdapter, "mark_governance_published", raiser), True
    if point == "owner_callback_post_commit":
        if hasattr(R, "checkpoint_evidence"):
            return mock.patch.object(R, "checkpoint_evidence", raiser), False
        return mock.patch.object(CR.ConfigBindingStore, "checkpoint", raiser), False
    raise ValueError(point)


POINTS = ["after_state", "after_journal", "binder_entry", "after_row", "before_commit", "owner_callback_post_commit"]
OPS = ["remember", "recall", "snapshot", "seam_then_checkpoint", "seam_then_base_checkpoint"]


def run_op(memory, op, i):
    d = memory.runtime.durable_runtime
    if op == "remember":
        memory.remember(f"memory:r{i}", f"Injected fact {i}.")
    elif op == "recall":
        memory.recall("deploy window")
    elif op == "snapshot":
        d.persist_visibility_snapshot(f"op:{i}", {"operation": {"required_projection_ids": []}})
    elif op == "seam_then_checkpoint":
        d.checkpoint()
    elif op == "seam_then_base_checkpoint":
        d.base.checkpoint()


def main():
    bad = 0
    for point in POINTS:
        for exc_type in (OSError, KeyboardInterrupt):
            for op in OPS:
                root = C.tmp() / "s"
                m = C.open_mem(root)
                m.remember("memory:x", "The deploy window is Thursday.")
                if op.startswith("seam"):
                    m.runtime.adapter.set_shared_domain_members(f"domain:{point}", ("agent:a", "agent:b"))
                rows, g, obs = C.tables(root), gov(m), m.runtime.durable_runtime.base._observed_generation
                p, pre_commit = patch_for(point, exc_type("inj"))
                if p is None:
                    m.close()
                    continue
                raised = None
                with p:
                    try:
                        run_op(m, op, 1)
                    except BaseException as e:  # noqa
                        raised = type(e).__name__
                problems = []
                if raised is None:
                    problems.append("no exception")
                after = C.inspect(root)
                if pre_commit:
                    if C.tables(root) != rows:
                        problems.append("durable rows changed")
                    if gov(m) != g:
                        problems.append("in-memory governance not restored")
                    if m.runtime.durable_runtime.base._observed_generation != obs:
                        problems.append("observed generation moved")
                else:
                    if after["state_gen"] != obs + 1 or after["row_gen"] not in (None, obs + 1):
                        problems.append(f"post-commit state {after}")
                # the handle keeps working
                try:
                    m.remember("memory:after", "Follow-up fact.")
                    follow = "follow-up ok"
                except BaseException as e:  # noqa
                    follow = f"follow-up {type(e).__name__}: {e}"
                    if pre_commit:
                        problems.append(follow)
                m.close()
                after = C.inspect(root)
                if after["row_gen"] is not None and after["row_gen"] != after["state_gen"]:
                    problems.append(f"SPLIT {after}")
                reopened = C.try_open(root)
                if not reopened.startswith(f"OK gen={after['state_gen']}"):
                    problems.append("reopen: " + reopened)
                if op.startswith("seam"):
                    m2 = C.open_mem(root)
                    members = m2.runtime.adapter.export_checkpoint_state()
                    present = f"domain:{point}" in json.dumps(members)
                    m2.close()
                    if not present:
                        problems.append("seam change lost")
                flag = "  <-- PROBLEM: " + "; ".join(problems) if problems else ""
                if problems:
                    bad += 1
                print(f"{point:27s} {exc_type.__name__:17s} {op:26s} raised={raised} {follow} state={after['state_gen']} row={after['row_gen']} file={after['file_gen']} reopen={reopened}{flag}")
    print(f"PROBLEMS: {bad}")


if __name__ == "__main__":
    main()
