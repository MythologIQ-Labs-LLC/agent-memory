"""#769 validation: opt-in competition observer overhead on durable SQLite stores.

For each scale (default 1,000 / 3,000 / 10,000 memories) a deterministic
corpus is written through the governed ``retain`` path into a real
ConfiguredCompositionRuntime, then the store is recovered from disk and:

* default recall is timed cold (first call after recovery) and warm;
* the observer is timed cold (first call after recovery, which builds the
  adapter's semantic slot index) and warm;
* substrate reads issued by ONE observer call are counted (``get_fact`` rows
  and ``all_facts`` full-table materialisations) -> read amplification per
  admitted reference;
* default-recall equivalence is checked between a recovered store on which
  the observer ran and an independently recovered twin on which it never ran.

Cold = fresh SQLite connection and empty in-process caches; the OS page cache
is not dropped (no root in the container), so cold numbers are a lower bound.

Usage: python benchmark_observer_overhead.py --repo <checkout> --out <json> [--sizes 1000 3000 10000]
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

QUERY = "Aster service endpoint"
WARM_RUNS = 15


def _setup(repo: Path):
    sys.path.insert(0, str(repo / "reference"))
    from agentmem_ref.recall_control import (
        ControlledRecallPlanner, RecallControlPlan, RecallRouteBudget,
    )
    from agentmem_ref.runtime import typed_proposition as typed
    from agentmem_ref.runtime.configured_restart import ConfigBoundRestartRuntime
    from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
    from agentmem_ref.runtime.runtime_composition import (
        ConfiguredCompositionRuntime, LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE,
        SHARED_EVIDENCE_ROUTE,
    )
    from tests.test_recall_control import _plan, _proposal, _context, TENANT, PROJECT, _FixedController
    return dict(locals())


def _typed(api, subject, attribute, value):
    typed = api["typed"]
    validated = typed.validate({"subject": subject, "attribute": attribute, "value": value,
                                "assertion": "state", "cardinality": "single", "flags": {}})
    return {"typed_proposition": typed.typed_record(validated, typed.CALLER_DECLARED)}


def build(api, root: Path, size: int) -> dict:
    rng = random.Random(size)
    rt = api["ConfiguredCompositionRuntime"].create(root, tenant=api["TENANT"], plan=api["_plan"]())
    words = ("alpha", "beta", "gamma", "delta", "router", "cache", "queue", "billing",
             "service", "endpoint", "latency", "owner", "region", "deploy", "token")
    counts = {"target_typed": 0, "target_untyped": 0, "other_typed": 0, "hidden": 0, "filler": 0}
    started = time.perf_counter()
    for i in range(size):
        name = f"memory:m{i}"
        project = api["PROJECT"]
        typed_write = None
        if i % 250 == 0:
            value = ("/v1", "/v2")[(i // 250) % 2]
            text, typed_write = f"Aster service endpoint is {value}", _typed(api, "Aster service", "endpoint", value)
            counts["target_typed"] += 1
        elif i % 125 == 0:
            text = f"Aster service endpoint note {i} mentions a migration"
            counts["target_untyped"] += 1
        elif i % 3 == 0:
            k = i % max(size // 4, 1)
            text = f"service-{k} {rng.choice(('endpoint', 'owner'))} is /{rng.choice(words)}{i}"
            typed_write = _typed(api, f"service-{k}", text.split()[1], f"/{i}")
            counts["other_typed"] += 1
        else:
            text = " ".join(rng.choice(words) for _ in range(8)) + f" {i}"
            counts["filler"] += 1
        if i % 20 == 7:
            project = "project-hidden"
            counts["hidden"] += 1
        kw = {"typed_write": typed_write} if typed_write else {}
        out = rt.retain(api["_proposal"](name, evidence_refs=(f"session:{i}",), project_ref=project), text, **kw)
        assert out.committed, out
    return {"build_seconds": round(time.perf_counter() - started, 3), "corpus": counts}


def recover(api, root: Path):
    durable = api["ConfigBoundRestartRuntime"].recover(root, plan=api["_plan"]())
    rt = api["ConfiguredCompositionRuntime"](durable_runtime=durable, plan=api["_plan"]())
    planner = api["ControlledRecallPlanner"](rt.adapter, controller=api["_FixedController"](
        api["RecallControlPlan"](
            controller_ref="validation:769-bench", controller_version="1",
            route_budgets=(api["RecallRouteBudget"](api["LEXICAL_ROUTE"], 20),
                           api["RecallRouteBudget"](api["EXACT_IDENTITY_ROUTE"], 0),
                           api["RecallRouteBudget"](api["SHARED_EVIDENCE_ROUTE"], 0)))))
    return rt, planner


class ReadCounter:
    def __init__(self, substrate):
        self.substrate = substrate
        self.get_fact = 0
        self.all_facts = 0
        self.all_fact_rows = 0
        self._get, self._all = substrate.get_fact, substrate.all_facts

    def __enter__(self):
        def get_fact(uuid):
            self.get_fact += 1
            return self._get(uuid)

        def all_facts():
            rows = self._all()
            self.all_facts += 1
            self.all_fact_rows += len(rows)
            return rows
        self.substrate.get_fact, self.substrate.all_facts = get_fact, all_facts
        return self

    def __exit__(self, *exc):
        del self.substrate.get_fact, self.substrate.all_facts


def _ms(fn):
    started = time.perf_counter()
    value = fn()
    return (time.perf_counter() - started) * 1000, value


def _snapshot(result):
    return (list(result.admitted), list(result.ranked_admitted), dict(result.recall.refusals),
            result.observation_receipt.content_digest, result.stop_reason,
            dict(result.route_candidate_counts))


def measure(api, root: Path) -> dict:
    need = api["CoverageNeed"](api["typed"].typed_slot("Aster service", "endpoint"))
    ctx = api["_context"]()
    rt, planner = recover(api, root)
    substrate = rt.adapter.checkpoint_substrate()
    recall_cold, result = _ms(lambda: planner.recall(QUERY, ctx))
    recall_warm = [_ms(lambda: planner.recall(QUERY, ctx))[0] for _ in range(WARM_RUNS)]
    result = planner.recall(QUERY, ctx)
    with ReadCounter(substrate) as cold_reads:
        observe_cold, diagnostic = _ms(lambda: planner.observe_competition_diagnostic(result, ctx, needs=(need,)))
    with ReadCounter(substrate) as warm_reads:
        planner.observe_competition_diagnostic(result, ctx, needs=(need,))
    observe_warm = [_ms(lambda: planner.observe_competition_diagnostic(result, ctx, needs=(need,)))[0]
                    for _ in range(WARM_RUNS)]
    with ReadCounter(substrate) as recall_reads:
        planner.recall(QUERY, ctx)
    admitted = len(result.admitted)
    # Equivalence: observer-touched store vs an independently recovered twin.
    _rt2, twin = recover(api, root)
    queries = (QUERY, "service endpoint owner", "billing latency", "router cache deploy", "token region")
    equivalent = all(_snapshot(planner.recall(q, ctx)) == _snapshot(twin.recall(q, ctx)) for q in queries)
    return {
        "admitted_refs": admitted,
        "diagnostic": diagnostic.to_dict(),
        "default_recall_ms": {"cold": round(recall_cold, 2), "warm_median": round(statistics.median(recall_warm), 2),
                              "warm_p90": round(sorted(recall_warm)[int(0.9 * (WARM_RUNS - 1))], 2)},
        "observer_ms": {"cold": round(observe_cold, 2), "warm_median": round(statistics.median(observe_warm), 2),
                        "warm_p90": round(sorted(observe_warm)[int(0.9 * (WARM_RUNS - 1))], 2)},
        "observer_reads": {
            "cold": {"get_fact": cold_reads.get_fact, "all_facts_calls": cold_reads.all_facts,
                     "all_facts_rows": cold_reads.all_fact_rows},
            "warm": {"get_fact": warm_reads.get_fact, "all_facts_calls": warm_reads.all_facts,
                     "all_facts_rows": warm_reads.all_fact_rows},
            "warm_get_fact_per_admitted_ref": round(warm_reads.get_fact / max(admitted, 1), 2),
        },
        "default_recall_reads": {"get_fact": recall_reads.get_fact, "all_facts_calls": recall_reads.all_facts,
                                 "all_facts_rows": recall_reads.all_fact_rows},
        "default_recall_equivalent_with_and_without_observer": equivalent,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1000, 3000, 10000])
    args = parser.parse_args()
    api = _setup(args.repo)
    head = subprocess.run(["git", "-C", str(args.repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    rows = []
    for size in args.sizes:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            built = build(api, root, size)
            row = {"memories": size, **built, **measure(api, root)}
            row["sqlite_bytes"] = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("memories", "build_seconds", "default_recall_ms",
                                              "observer_ms", "observer_reads")}), flush=True)
    report = {"schema": "769-observer-overhead-v1", "runtime_head": head,
              "python": platform.python_version(), "platform": platform.platform(),
              "warm_runs": WARM_RUNS, "results": rows}
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
