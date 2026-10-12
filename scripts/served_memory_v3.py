#!/usr/bin/env python3
"""#771 lifecycle v3: declared evaluation instant (R-A2) and separated provenance (R-A3).

R-A2  ``served-memory-lifecycle-v3`` inputs are v2 lifecycle inputs plus a
      REQUIRED ``reference_time``: the explicitly declared, timezone-aware
      instant at which current-intent questions are asked. v2 inputs are
      never reinterpreted: they keep their meaning (no declared instant) and
      a v2 document carrying ``reference_time`` is still rejected by v2
      validation. ``derive_v3`` writes a NEW document; it never edits v2.

R-A3  ``served-memory-run-v2`` manifests record, separately:
        evaluator.commit / clean        the checkout whose scripts ran
        runtime.commit / clean          the checkout whose runtime executed
        runtime.protected_tree          git tree object of reference/agentmem_ref
                                        at runtime.commit (protected source identity)
        runtime.loaded_module(+_blob)   the runtime_composition.py actually imported
        input_sha256, reference_time    execution inputs
      The evaluator commit is never presented as the runtime revision. The
      qualifier re-derives the protected tree and module blob from
      runtime.commit in a repository it is given and refuses on mismatch.

The runner must be started with ``--runtime-root``; the runtime is imported
from that root BEFORE any evaluator module that could import another copy.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_V3 = "served-memory-lifecycle-v3"
RUN_SCHEMA_V2 = "served-memory-run-v2"
PROTECTED_DIR = "reference/agentmem_ref"
MODULE = "reference/agentmem_ref/runtime/runtime_composition.py"
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")


# ---------------------------------------------------------------- R-A2 instant
def parse_reference_time(value) -> datetime:
    """Strict zone-aware instant. Ambiguous or unzoned forms are refused."""
    if type(value) is not str or not _INSTANT.fullmatch(value):
        raise ValueError("reference_time must be a full ISO-8601 instant with Z or +HH:MM offset")
    if value.endswith("-00:00"):
        raise ValueError("reference_time offset -00:00 means 'unknown local offset'; refuse as ambiguous")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("reference_time is not a valid calendar instant") from exc
    if parsed.utcoffset() is None:
        raise ValueError("reference_time must carry an offset")
    return parsed.astimezone(timezone.utc)


def _v2_view(data):
    if type(data) is not dict or data.get("schema") != SCHEMA_V3 or "reference_time" not in data:
        raise ValueError("invalid lifecycle v3 input; reference_time is required")
    view = {k: v for k, v in data.items() if k != "reference_time"}
    view["schema"] = "served-memory-lifecycle-v2"
    return view


def validate_inputs_v3(data, lifecycle):
    parse_reference_time(data.get("reference_time") if type(data) is dict else None)
    lifecycle.validate_inputs(_v2_view(data))
    return data


def canonical_input_digest_v3(data, lifecycle) -> str:
    validate_inputs_v3(data, lifecycle)
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def derive_v3(v2_inputs: dict, reference_time: str) -> dict:
    """New v3 document from frozen v2 inputs; the v2 document is not modified."""
    parse_reference_time(reference_time)
    if type(v2_inputs) is not dict or v2_inputs.get("schema") != "served-memory-lifecycle-v2":
        raise ValueError("derive_v3 requires a v2 lifecycle document")
    derived = copy.deepcopy(v2_inputs)
    derived["schema"] = SCHEMA_V3
    derived["reference_time"] = reference_time
    return derived


def temporally_inapplicable(data, lifecycle) -> list[str]:
    """Fact ids whose caller-declared window does not cover the reference instant."""
    instant = parse_reference_time(data["reference_time"])
    out = []
    for event in data["events"]:
        temporal = event.get("temporal")
        if not temporal or event["op"] == "delete":
            continue
        start = temporal.get("valid_from")
        end = temporal.get("valid_until")
        if (start and parse_reference_time(start) > instant) or (end and parse_reference_time(end) <= instant):
            out.append(event["id"])
    return sorted(out)


# ---------------------------------------------------------------- R-A3 identity
def _git(root: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


def _checkout(root: Path, *, paths=()) -> dict:
    commit = _git(root, "rev-parse", "HEAD")
    dirty = _git(root, "status", "--porcelain", "--", *paths) if paths else _git(root, "status", "--porcelain")
    return {"commit": commit, "clean": dirty == ""}


def load_runtime(runtime_root: Path):
    """Import agentmem_ref from runtime_root, then the evaluator modules; verify which ran."""
    runtime_root = Path(runtime_root).resolve()
    if "agentmem_ref" in sys.modules:
        raise RuntimeError("a runtime was already imported in this process; refuse ambiguous identity")
    sys.path.insert(0, str(runtime_root / "reference"))
    import agentmem_ref.runtime_composition  # noqa: F401
    loaded = Path(sys.modules["agentmem_ref.runtime.runtime_composition"].__file__).resolve()
    if loaded != runtime_root / MODULE:
        raise RuntimeError(f"runtime module loaded from {loaded}, not from {runtime_root}")
    sys.path.insert(0, str(EVAL_ROOT / "scripts"))
    import run_served_memory_lifecycle_scenarios as lifecycle
    if Path(sys.modules["agentmem_ref.runtime.runtime_composition"].__file__).resolve() != loaded:
        raise RuntimeError("evaluator import replaced the runtime under test")
    return lifecycle, loaded


def runtime_provenance(runtime_root: Path, loaded: Path) -> dict:
    runtime_root = Path(runtime_root).resolve()
    info = _checkout(runtime_root, paths=(PROTECTED_DIR,))
    if not info["clean"]:
        raise RuntimeError("runtime protected source has uncommitted changes; identity unprovable")
    blob = _git(runtime_root, "hash-object", str(loaded))
    committed = _git(runtime_root, "rev-parse", f"{info['commit']}:{MODULE}")
    if blob != committed:
        raise RuntimeError("loaded runtime module differs from the committed source")
    return {"commit": info["commit"], "clean": True,
            "protected_tree": _git(runtime_root, "rev-parse", f"{info['commit']}:{PROTECTED_DIR}"),
            "loaded_module": MODULE, "loaded_module_blob": blob}


def verify_runtime_provenance(provenance: dict, repo: Path) -> None:
    """Re-derive identity from runtime.commit in ``repo``; refuse any mismatch."""
    if type(provenance) is not dict or set(provenance) != {"evaluator", "runtime"}:
        raise ValueError("manifest provenance must separate evaluator and runtime")
    runtime, evaluator = provenance["runtime"], provenance["evaluator"]
    if (type(runtime) is not dict or set(runtime) != {"commit", "clean", "protected_tree", "loaded_module",
                                                       "loaded_module_blob"}
            or type(evaluator) is not dict or set(evaluator) != {"commit", "clean"}):
        raise ValueError("incomplete runtime or evaluator provenance")
    for value in (runtime["commit"], evaluator["commit"], runtime["protected_tree"], runtime["loaded_module_blob"]):
        if type(value) is not str or not _HEX40.fullmatch(value):
            raise ValueError("provenance identities must be full 40-hex git object ids")
    if runtime["clean"] is not True or evaluator["clean"] is not True or runtime["loaded_module"] != MODULE:
        raise ValueError("provenance requires clean checkouts and the canonical runtime module path")
    try:
        tree = _git(repo, "rev-parse", f"{runtime['commit']}:{PROTECTED_DIR}")
        blob = _git(repo, "rev-parse", f"{runtime['commit']}:{MODULE}")
        _git(repo, "cat-file", "-e", evaluator["commit"] + "^{commit}")
    except subprocess.CalledProcessError as exc:
        raise ValueError("cannot resolve recorded runtime/evaluator commits; identity unverifiable") from exc
    if tree != runtime["protected_tree"]:
        raise ValueError("recorded protected tree does not match runtime.commit")
    if blob != runtime["loaded_module_blob"]:
        raise ValueError("recorded runtime module blob does not match runtime.commit")


# ---------------------------------------------------------------- run / qualify
def run_v3(data, store_root: Path, *, runtime_root: Path, lane_id: str, backend: str, lifecycle, loaded):
    validate_inputs_v3(data, lifecycle)
    lifecycle._name(lane_id, "lane id")
    if backend not in ("composed-multiroute", "governed-lexical"):
        raise ValueError("unsupported governed reference backend")
    # Recorded, not enforced here: the qualifier refuses unclean manifests.
    evaluator = _checkout(EVAL_ROOT)
    runtime = runtime_provenance(runtime_root, loaded)
    instant = data["reference_time"]
    runtime_obj, labels = lifecycle.build_store(_v2_view(data), Path(store_root))
    context = lifecycle.RecallContext(target_domain_refs=(data["tenant"], data["project"]),
                                      principal_ref="agent:quality-evaluation",
                                      project_ref=data["project"], purpose=data["purpose"])
    rows, applied = [], []
    for q in data["queries"]:
        if backend == "composed-multiroute":
            mode = {"current": "current", "historical": "historical",
                    "timeless": "atemporal_or_unspecified"}[q["intent"]]
            intent = {"mode": mode}
            if mode == "current":
                intent["reference_time"] = instant
                applied.append(q["id"])
            result = runtime_obj.multi_route_recall(q["query"], context, temporal_intent=intent)
            ranked = result.ranked_admitted
        else:
            result = runtime_obj.recall(q["query"], context)
            ranked = result.admitted
        if len(ranked) != len(set(ranked)) or not set(ranked).issubset(result.admitted):
            raise RuntimeError("ranking violates governed admission")
        if any(r not in labels for r in ranked):
            raise RuntimeError("unmapped governed result ID")
        rows.append({"id": q["id"], "returned": [labels[r] for r in ranked[:q["budget"]]]})
    return {
        "schema": RUN_SCHEMA_V2, "lane_id": lane_id, "execution_backend": backend,
        "input_sha256": canonical_input_digest_v3(data, lifecycle),
        "reference_time": instant,
        "reference_time_utc": parse_reference_time(instant).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "reference_time_applied_to": applied,
        "provenance": {"evaluator": evaluator, "runtime": runtime},
        "rows": rows,
    }


def qualify_v3(inputs, gold, manifest, *, repo: Path):
    """Verify identity and lifecycle/temporal gold integrity, then score."""
    sys.path.insert(0, str(EVAL_ROOT / "scripts"))
    import run_served_memory_lifecycle_scenarios as lifecycle
    from qualify_served_memory_run import _qualify_lifecycle
    validate_inputs_v3(inputs, lifecycle)
    if type(manifest) is not dict or set(manifest) != {
        "schema", "lane_id", "execution_backend", "input_sha256", "reference_time",
        "reference_time_utc", "reference_time_applied_to", "provenance", "rows",
    } or manifest["schema"] != RUN_SCHEMA_V2:
        raise ValueError("v3 qualification requires a served-memory-run-v2 manifest")
    if manifest["input_sha256"] != canonical_input_digest_v3(inputs, lifecycle):
        raise ValueError("run executed with a different input corpus")
    if manifest["reference_time"] != inputs["reference_time"]:
        raise ValueError("run reference instant differs from the declared input instant")
    if manifest["reference_time_utc"] != parse_reference_time(inputs["reference_time"]).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"):
        raise ValueError("normalized reference instant mismatch")
    inapplicable = set(temporally_inapplicable(inputs, lifecycle))
    for case in gold["cases"] if type(gold) is dict and type(gold.get("cases")) is list else []:
        if type(case) is dict and case.get("intent") == "current" and not inapplicable.issubset(
                set(case.get("stale", [])) | set(case.get("prohibited", []))):
            raise ValueError("facts outside their declared window at reference_time must be stale "
                             "for current-intent questions")
    verify_runtime_provenance(manifest["provenance"], Path(repo))
    scorer_run = {"schema": "served-memory-run-v1",
                  "runtime_revision": manifest["provenance"]["runtime"]["commit"],
                  "lane_id": manifest["lane_id"], "execution_backend": manifest["execution_backend"],
                  "input_sha256": lifecycle.canonical_input_digest(_v2_view(inputs)),
                  "rows": manifest["rows"]}
    report = _qualify_lifecycle(_v2_view(inputs), gold, scorer_run)
    report["runtime_revision"] = None  # superseded by the separated provenance block below
    report["provenance"] = manifest["provenance"]
    report["reference_time"] = manifest["reference_time"]
    report["input_sha256"] = manifest["input_sha256"]
    report["gold_sha256"] = hashlib.sha256(json.dumps(gold, sort_keys=True, separators=(",", ":"),
                                                      ensure_ascii=False).encode("utf-8")).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--runtime-root", type=Path, required=True)
    r.add_argument("--inputs", type=Path, required=True)
    r.add_argument("--store", type=Path, required=True)
    r.add_argument("--output", type=Path, required=True)
    r.add_argument("--lane-id", required=True)
    r.add_argument("--backend", choices=("composed-multiroute", "governed-lexical"), default="composed-multiroute")
    d = sub.add_parser("derive")
    d.add_argument("--v2-inputs", type=Path, required=True)
    d.add_argument("--reference-time", required=True)
    d.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "derive":
        if args.output.exists():
            parser.error("refusing to overwrite")
        doc = derive_v3(json.loads(args.v2_inputs.read_text(encoding="utf-8")), args.reference_time)
        args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    if args.output.exists() or args.store.exists():
        parser.error("output and store paths must not preexist")
    lifecycle, loaded = load_runtime(args.runtime_root)
    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    manifest = run_v3(data, args.store, runtime_root=args.runtime_root, lane_id=args.lane_id,
                      backend=args.backend, lifecycle=lifecycle, loaded=loaded)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
