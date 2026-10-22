"""P1: is every refusal side-effect free? And which ungoverned in-memory mutations are silently bound later?

For each act: snapshot adapter export + raw rows, run the act outside a generation on a facade-owned
handle, compare; then run one facade recall (a supported generation) and check whether the act's
effect was published into durable state; then close/reopen.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403
from agentmem_ref.runtime.contextual_recall_adapter import admit_preselected_candidates
from agentmem_ref.runtime import shared_revocation


def case(name, act):
    root, m = fresh()
    before_gov, before_rows, g0 = gov_state(m), rows(root), gen(m)
    try:
        out = act(m)
        call = f"returned {str(out)[:40]!r}"
    except Exception as exc:  # noqa: BLE001
        call = f"raised {type(exc).__name__}"
    after_gov, after_rows = gov_state(m), rows(root)
    changed_gov = diff_keys(before_gov, after_gov)
    changed_rows = [t for t in after_rows if after_rows[t] != before_rows.get(t)]
    detail = ""
    if "clock_tick" in changed_gov:
        detail = f" clock {before_gov['clock_tick']}->{after_gov['clock_tick']}"
    # a later supported generation: does it publish the refused/ungoverned act's effect?
    m.recall("deploy window")
    m.close()
    m2 = opened(root)
    ref_root, ref = fresh()  # identical history without the act
    ref.recall("deploy window")
    ref.close()
    ref2 = opened(ref_root)
    bound = diff_keys(gov_state(ref2), gov_state(m2))
    bound = [k for k in bound if k not in ()]  # report every differing governance key
    m2.close(); ref2.close()
    print(f"{name:42s} | {call:34s} | adapter-export changed: {changed_gov}{detail} | rows changed: {changed_rows} "
          f"| gen {g0}->{gen(m) if False else '-'} | durably bound after next facade op: {bound}")


ctx = lambda m: m._handle_recall_context()  # noqa: E731
fact = lambda m: m.runtime.adapter.current_fact_uuid("memory:x")  # noqa: E731

case("adapter.governed_recall", lambda m: m.runtime.adapter.governed_recall("deploy", ctx(m)))
case("admit_preselected_candidates", lambda m: admit_preselected_candidates(m.runtime.adapter, [fact(m)], ctx(m)))
case("recall_planner.recall", lambda m: m.runtime.recall_planner.recall("deploy", ctx(m)))
case("ConfiguredCompositionRuntime.multi_route (base cls)",
     lambda m: type(m.runtime).__mro__[1].multi_route_recall(m.runtime, "deploy", ctx(m)))
case("projections.correct (record_correction)", lambda m: m.runtime.projections.correct("memory:x"))
case("adapter.record_correction", lambda m: m.runtime.adapter.record_correction("memory:x"))
case("adapter.set_shared_domain_members",
     lambda m: m.runtime.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:evil")))
case("shared_revocation.bootstrap_shared_domain_members",
     lambda m: shared_revocation.bootstrap_shared_domain_members(m.runtime.adapter, "shared:y", ("agent:evil",)))
case("adapter.extension_state[...] = ...",
     lambda m: m.runtime.adapter.extension_state.__setitem__("probe", {"x": 1}))
case("adapter.events.append",
     lambda m: m.runtime.adapter.events.append({"event_id": "forged", "event_type": "memory.commit"}))
case("rebuild_projection", lambda m: m.runtime.rebuild_projection())
