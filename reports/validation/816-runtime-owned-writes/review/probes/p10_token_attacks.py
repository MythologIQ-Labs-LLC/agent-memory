"""P10: try to break the dc7d3f3f generation token (substrate.generation_opened / _generation_thread)."""
import sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403


def token(m):
    return m.runtime.adapter.checkpoint_substrate()._ids._generation_thread


def report(name, fn):
    root, m = fresh()
    try:
        out = fn(m)
    except BaseException as exc:  # noqa: BLE001
        out = f"raised {type(exc).__name__}: {str(exc)[:70]}"
    tok = token(m)
    try:
        m.recall("deploy window"); after = "facade recall OK"
    except Exception as exc:  # noqa: BLE001
        after = f"facade recall FAILED {type(exc).__name__}: {exc}"
    m.close()
    print(f"{name:52s} | {out} | token after: {tok} | {after} | {try_reopen(root)}")


ctx = lambda m: m._handle_recall_context()  # noqa: E731
run = lambda m, op: m.runtime.durable_runtime.run_governed_read(op)  # noqa: E731
base = lambda m: m.runtime.durable_runtime.base  # noqa: E731


def nested_checkpoint(m):
    def op():
        try:
            base(m).checkpoint()
            inner = "inner checkpoint ran"
        except Exception as exc:  # noqa: BLE001
            inner = f"inner checkpoint {type(exc).__name__}: {exc}"
        m.runtime.adapter.mint_id()  # outer generation must still be allowed to allocate
        return inner + "; outer still allocates"
    return run(m, op)


def nested_run(m):
    def op():
        try:
            run(m, lambda: m.runtime.adapter.mint_id())
            inner = "inner generation ran"
        except Exception as exc:  # noqa: BLE001
            inner = f"inner {type(exc).__name__}: {exc}"
        m.runtime.adapter.mint_id()
        return inner + "; outer still allocates"
    return run(m, op)


def nested_generation_opened(m):
    sub = m.runtime.adapter.checkpoint_substrate()

    def op():
        with sub.generation_opened():
            pass
        m.runtime.adapter.mint_id()  # after a nested marker exits, is the outer token still there?
        return "outer still allocates"
    return run(m, op)


def forge_token(m):
    sub = m.runtime.adapter.checkpoint_substrate()
    with sub.transaction(), sub.generation_opened():
        r = m.runtime.adapter.governed_recall("deploy", ctx(m))
    return f"forged generation NOT refused; admitted {r.admitted}"


def leak_after_exception(m):
    try:
        run(m, lambda: (_ for _ in ()).throw(ValueError("boom")))
    except ValueError:
        pass
    try:
        m.runtime.adapter.mint_id(); return "LEAK: direct mint_id allowed after failed generation"
    except Exception as exc:  # noqa: BLE001
        return f"direct mint_id after failed generation: {type(exc).__name__}"


def leak_after_hook_failure(m):
    from unittest import mock
    from agentmem_ref.runtime import configured_restart
    def boom(*a, **k): raise OSError("binding write failed")
    with mock.patch.object(configured_restart.ConfigBindingStore, "checkpoint", boom):
        try:
            m.recall("deploy window")
        except OSError:
            pass
    try:
        m.runtime.adapter.mint_id(); return "LEAK: direct mint_id allowed after hook failure"
    except Exception as exc:  # noqa: BLE001
        return f"direct mint_id after hook failure: {type(exc).__name__}"


def worker_thread_inside_generation(m):
    res = {}

    def op():
        def w():
            try:
                m.runtime.adapter.mint_id(); res["w"] = "worker allocated"
            except Exception as exc:  # noqa: BLE001
                res["w"] = f"worker refused {type(exc).__name__}"
        t = threading.Thread(target=w); t.start(); t.join()
        return res["w"]
    return run(m, op)


def other_thread_holds_lock_outside_generation(m):
    # a direct caller that holds the serialization lock (documented contract) on another thread
    res = {}

    def w():
        with m.runtime.serialization_lock:
            try:
                m.runtime.adapter.governed_recall("deploy", ctx(m)); res["w"] = "NOT refused"
            except Exception as exc:  # noqa: BLE001
                res["w"] = f"refused {type(exc).__name__}"
    t = threading.Thread(target=w); t.start(); t.join()
    return res["w"]


def lazy_result_after_generation(m):
    # an operation that returns a callable executed after the generation closed
    f = run(m, lambda: (lambda: m.runtime.adapter.mint_id()))
    try:
        f(); return "LEAK: deferred allocation allowed"
    except Exception as exc:  # noqa: BLE001
        return f"deferred allocation: {type(exc).__name__}"


def clock_read_paths(m):
    a = m.runtime.adapter
    out = []
    for name, f in (("adapter.now", a.now), ("adapter._clock.now", a._clock.now)):
        try:
            f(); out.append(f"{name} allowed")
        except Exception as exc:  # noqa: BLE001
            out.append(f"{name} {type(exc).__name__}")
    # can a caller just remove the guard?
    a._clock.guard = None
    try:
        a._clock.now(); out.append("clock guard removable by assignment (tick moved)")
    except Exception as exc:  # noqa: BLE001
        out.append(f"guard None still refused {type(exc).__name__}")
    return "; ".join(out)


report("nested checkpoint inside an operation", nested_checkpoint)
report("nested run_governed_read inside an operation", nested_run)
report("nested generation_opened inside an operation", nested_generation_opened)
report("forged token: transaction()+generation_opened()", forge_token)
report("token after a failed generation", leak_after_exception)
report("token after binding-hook failure", leak_after_hook_failure)
report("worker thread spawned inside a generation", worker_thread_inside_generation)
report("other thread holding the lock, no generation", other_thread_holds_lock_outside_generation)
report("deferred callable run after generation", lazy_result_after_generation)
report("clock reads outside a generation", clock_read_paths)
