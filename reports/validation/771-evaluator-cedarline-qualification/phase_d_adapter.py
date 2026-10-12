"""#771/#773 validation-only serving adapter. Never imported by any runtime.

Runs ONE serving mode against ONE runtime checkout, in its own process, over
the governed lifecycle history of a frozen corpus (built by the evaluator's
lifecycle runner, gold never loaded). Modes:

  composed-default  multi_route_recall with the declared intent only
                    (identical to the lifecycle runner's composed backend)
  composed-T        as above, but current-intent questions also carry the
                    explicit reference instant T
  selector-T        current-intent questions use the #773 opt-in
                    current_served_context(budget, reference_time=T);
                    historical/timeless questions use composed-T unchanged

Output: a served-memory-run-v1 manifest (qualifiable by the evaluator) and a
sidecar with runtime identity, per-question applicability labels of every
admitted candidate, selector exclusions and refusals.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parents[3]


def _load(runtime_root: Path):
    sys.path.insert(0, str(runtime_root / "reference"))
    import agentmem_ref.runtime_composition as rc  # noqa: F401
    loaded = Path(sys.modules["agentmem_ref.runtime.runtime_composition"].__file__).resolve()
    if not str(loaded).startswith(str(runtime_root.resolve())):
        raise RuntimeError(f"wrong runtime loaded: {loaded}")
    sys.path.insert(0, str(EVAL_ROOT / "scripts"))
    import run_served_memory_lifecycle_scenarios as lifecycle
    again = Path(sys.modules["agentmem_ref.runtime.runtime_composition"].__file__).resolve()
    if again != loaded:
        raise RuntimeError("runner import replaced the runtime under test")
    from agentmem_ref.adapter import RecallContext
    return lifecycle, RecallContext, loaded


def _git(root: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--mode", choices=("composed-default", "composed-T", "selector-T"), required=True)
    parser.add_argument("--reference-time", default="2026-10-12T12:00:00Z")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lifecycle, RecallContext, loaded = _load(args.runtime_root)
    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    T = args.reference_time
    with tempfile.TemporaryDirectory() as tmp:
        runtime, labels = lifecycle.build_store(data, Path(tmp) / "store")
        context = RecallContext(target_domain_refs=(data["tenant"], data["project"]),
                                principal_ref="agent:quality-evaluation",
                                project_ref=data["project"], purpose=data["purpose"])
        rows, sidecar = [], []
        for q in data["queries"]:
            mode = {"current": "current", "historical": "historical",
                    "timeless": "atemporal_or_unspecified"}[q["intent"]]
            intent = {"mode": mode}
            if args.mode != "composed-default" and mode == "current":
                intent["reference_time"] = T
            result = runtime.multi_route_recall(q["query"], context, temporal_intent=intent)
            ranked = list(result.ranked_admitted)
            applicability = {labels[r]: result.ranking_evidence.get(r, {}).get("temporal_applicability")
                             for r in ranked}
            extra = {"id": q["id"], "intent": q["intent"], "applicability": applicability,
                     "ranked_admitted": [labels[r] for r in ranked]}
            if args.mode == "selector-T" and mode == "current":
                try:
                    selected = runtime.current_served_context(q["query"], context, budget=q["budget"],
                                                              reference_time=T)
                    served = list(selected.served_refs)
                    extra.update(selector="served", known_inapplicable_count=selected.known_inapplicable_count,
                                 unknown_applicability_count=selected.unknown_applicability_count)
                except ValueError as exc:
                    served = []
                    extra.update(selector="refused", refusal=str(exc))
                extra["excluded_known_inapplicable"] = [
                    labels[r] for r in ranked
                    if applicability[labels[r]] not in ("applicable", "unknown_temporal_basis")]
            else:
                served = ranked[:q["budget"]]
            if any(r not in labels for r in served):
                raise RuntimeError("unmapped served identity")
            rows.append({"id": q["id"], "returned": [labels[r] for r in served]})
            extra["served"] = rows[-1]["returned"]
            sidecar.append(extra)
    run = {"schema": "served-memory-run-v1", "runtime_revision": _git(args.runtime_root, "rev-parse", "HEAD"),
           "lane_id": "phase-d-" + args.mode, "execution_backend": "composed-multiroute",
           "input_sha256": lifecycle.canonical_input_digest(data), "rows": rows}
    identity = {
        "runtime_root_head": run["runtime_revision"],
        "runtime_tree_clean": _git(args.runtime_root, "status", "--porcelain", "--", "reference") == "",
        "runtime_composition_path": str(loaded),
        "runtime_composition_blob": _git(args.runtime_root, "hash-object", str(loaded)),
        "evaluator_head": _git(EVAL_ROOT, "rev-parse", "HEAD"),
        "mode": args.mode, "reference_time": T,
    }
    args.out.write_text(json.dumps({"run": run, "identity": identity, "per_query": sidecar},
                                   indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
