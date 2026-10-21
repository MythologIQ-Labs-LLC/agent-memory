"""P4: the documented module-level API stages (docs/44: surface.commit/recall/forget/authorize/witness take
an adapter) on a facade-owned SQLite handle's adapter. What does the caller get: a contract result
envelope or an uncaught exception? Does the run_governed_read route work and reopen?
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403
from agentmem_ref.api import surface

FIX = Path(REF) / "fixtures" / "api"
action = json.loads((FIX / "action-envelope.example.json").read_text())
observation = json.loads((FIX / "execution-observation.example.json").read_text())


def attempt(name, fn, wrap):
    root, m = fresh()
    a = m.runtime.adapter
    call = (lambda: m.runtime.durable_runtime.run_governed_read(lambda: fn(m, a))) if wrap else (lambda: fn(m, a))
    try:
        r = call()
        out = f"result stage={r.get('stage')} refusal={r.get('refusal')!r}"
    except Exception as exc:  # noqa: BLE001
        out = f"EXCEPTION {type(exc).__name__}: {str(exc)[:60]}"
    m.close()
    print(f"{name:10s} {'via run_governed_read' if wrap else 'direct (docs/44 form)':24s} -> {out} | {try_reopen(root)}")


ctxenv = lambda m: {"contract_version": "1.3.0", "target_domain_refs": list(m._domain_refs()),  # noqa: E731
                    "principal_ref": m.actor_id, "project_ref": m.scope, "purpose": m.purpose}
stages = {
    "authorize": lambda m, a: surface.authorize(a, action),
    "witness": lambda m, a: surface.witness(a, observation),
    "recall": lambda m, a: surface.recall(a, "deploy", ctxenv(m)),
    "commit": lambda m, a: surface.commit(a, m._proposal(target_reference="memory:z", operation="promotion",
                                                          fact_text="Lunch is at noon."), "Lunch is at noon."),
}
for name, fn in stages.items():
    for wrap in (False, True):
        attempt(name, fn, wrap)
