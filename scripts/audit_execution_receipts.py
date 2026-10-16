#!/usr/bin/env python3
"""Audit committed benchmark execution receipts against the #808 v1 contract (read-only).

Given a checkout of an evidence commit, for every ``reports/benchmarks/runs/**/*manifest.json``:

1. validate the manifest exactly as committed;
2. resolve each evidence pointer (repository-root relative per v1, or manifest-directory
   relative as some bundles wrote them), re-hash it, and record the base that resolved;
3. build an in-memory *mechanical projection* that changes only representation (pointer base,
   a single input digest for a multi-file input, an enum ``purpose``) and validate it, to show
   whether anything beyond metadata stands between the receipt and v1 conformance;
4. list the receipt gaps that block acceptance, each typed as ``metadata`` (fixable from
   committed evidence), ``evidence`` (needs evidence that was not captured) or ``governance``
   (needs an owner or reviewer decision).

It also recomputes the cross-run checks that the classification depends on (repeats,
denominators, harness equivalence against accepted lane rows) from raw committed files.
Nothing is written into the evidence tree; the report is printed as JSON.
"""
from __future__ import annotations

import argparse
import ast
import copy
import gzip
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}")
CALL_PURPOSES = {"generation", "embedding", "judge", "rerank", "other"}


def load_validator():
    path = Path(__file__).resolve().parent / "validate_benchmark_execution_manifest.py"
    spec = importlib.util.spec_from_file_location("execution_manifest_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def lane_input_digest(root: Path, components: list[str]) -> tuple[str, str] | None:
    """The frozen lane whose fixture digests equal ``components`` in order, and its ``input_sha256``.

    AMB lanes define the input digest as SHA-256 over the raw fixture bytes in order
    (``input_digest_rule``), enforced by ``scripts/import_amb_lane_evidence.py``. Reusing the
    lane value keeps self-run rows on the same input identity as the lane rows they are
    compared with; no new rule is introduced.
    """
    for lane_file in sorted((root / "reference/agentmem_ref/evaluation/lanes").glob("*.json")):
        dataset = json.loads(lane_file.read_text(encoding="utf-8")).get("dataset", {})
        if [f.get("sha256") for f in dataset.get("fixtures", [])] == components and dataset.get("input_sha256"):
            return dataset["input_sha256"], lane_file.stem
    return None


def resolve(root: Path, manifest_path: Path, uri: str) -> tuple[str | None, Path | None]:
    direct = root / uri
    if ".." not in uri.split("/") and direct.is_file():
        return "repo_root", direct
    for label, base in (("manifest_dir", manifest_path.parent), ("bundle_dir", manifest_path.parent.parent)):
        relative = (base / uri).resolve()
        if relative.is_file() and root.resolve() in relative.parents:
            return label, relative
    return None, None


def audit_manifest(validator, root: Path, path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    rel = str(path.relative_to(root))
    result: dict = {"manifest": rel, "run_id": manifest.get("run_id")}
    try:
        validator.validate(copy.deepcopy(manifest))
        result["as_committed"] = "valid"
    except Exception as exc:  # noqa: BLE001 - recorded, not raised
        result["as_committed"] = f"refused: {str(exc).splitlines()[0][:160]}"

    pointers = [("normalized_run", manifest["normalized_run"])] + [(a["kind"], a) for a in manifest["artifacts"]]
    bases, hashes, projected_uris = Counter(), [], {}
    for label, pointer in pointers:
        base, file = resolve(root, path, pointer["uri"])
        bases[base or "unresolved"] += 1
        ok = file is not None and sha256(file) == pointer["sha256"]
        hashes.append({"pointer": label, "uri": pointer["uri"], "base": base, "sha256_matches": ok})
        if file is not None:
            projected_uris[pointer["uri"]] = str(file.relative_to(root.resolve()))
    result["pointer_bases"] = dict(bases)
    result["evidence_rehash"] = {"files": len(hashes), "matching": sum(h["sha256_matches"] for h in hashes),
                                 "failures": [h for h in hashes if not h["sha256_matches"]]}

    projection, changes = copy.deepcopy(manifest), []
    for pointer in [projection["normalized_run"], *projection["artifacts"]]:
        if pointer["uri"] in projected_uris and projected_uris[pointer["uri"]] != pointer["uri"]:
            pointer["uri"] = projected_uris[pointer["uri"]]
            changes.append("pointer rebased to repository root")
    digest = projection["benchmark"]["input_sha256"]
    if "+" in digest:
        lane = lane_input_digest(root, digest.split("+"))
        if lane:
            projection["benchmark"]["input_sha256"] = lane[0]
            changes.append(f"multi-file input digest replaced by the frozen lane value (rule and value from {lane[1]})")
    result["input_digest_by_lane_rule"] = lane[0] if "+" in digest and lane else None
    for call in projection["inference"]["calls"]:
        if call["purpose"] not in CALL_PURPOSES:
            call["parameters"] = dict(call["parameters"])
            call["purpose"] = "generation"
            changes.append(f"free-text call purpose mapped to 'generation' (was {manifest_purpose(manifest, call)!r})")
    try:
        validator.validate(copy.deepcopy(projection))
        result["mechanical_projection"] = {"changes": sorted(set(changes)), "result": "valid"}
    except Exception as exc:  # noqa: BLE001
        result["mechanical_projection"] = {"changes": sorted(set(changes)), "result": f"refused: {str(exc).splitlines()[0][:160]}"}
    try:
        validator.validate(copy.deepcopy(projection), evidence_root=root)
        result["mechanical_projection"]["with_evidence_root"] = "valid"
    except Exception as exc:  # noqa: BLE001
        result["mechanical_projection"]["with_evidence_root"] = f"refused: {str(exc).splitlines()[0][:160]}"
    result["gaps"] = receipt_gaps(manifest, root, path)
    return result


def manifest_purpose(manifest: dict, call: dict) -> str:
    for original in manifest["inference"]["calls"]:
        if original["model_id"] == call["model_id"]:
            return original["purpose"]
    return call["purpose"]


def adapter_history(root: Path, adapter_id: str) -> dict | None:
    """Commits touching the adapter file; a single commit means the committed blob is the only one that ever existed."""
    if not (root / adapter_id).is_file():
        return None
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    commits = git("log", "--format=%H", "--", adapter_id).stdout.split()
    blob = git("rev-parse", f"HEAD:{adapter_id}").stdout.strip()
    # In a shallow clone the earliest visible commit may be a graft. The history is complete
    # only if that commit has a parent and the file does not exist in it (it was created there).
    created_in_view = bool(commits) and git("rev-parse", "--verify", "-q", f"{commits[-1]}^").returncode == 0 \
        and git("cat-file", "-e", f"{commits[-1]}^:{adapter_id}").returncode != 0
    return {"commits": len(commits) if created_in_view else None, "blob": blob}


def shim_parameters(bundle: Path) -> dict | None:
    """Prompt-set digest and request settings observed in a committed shim call log, if one exists."""
    logs = sorted(bundle.glob("shim-calls.jsonl*"))
    if not logs:
        return None
    raw = logs[0].read_bytes()
    lines = (gzip.decompress(raw) if logs[0].suffix == ".gz" else raw).decode().splitlines()
    requests = [json.loads(line)["request"] for line in lines if line and "request" in json.loads(line)]
    settings = Counter((key, json.dumps(req.get(key))) for req in requests
                       for key in ("temperature", "top_p", "seed", "max_tokens"))
    prompts = hashlib.sha256(json.dumps([req.get("messages") for req in requests], sort_keys=True,
                                        separators=(",", ":")).encode()).hexdigest()
    return {"log": logs[0].name, "chat_requests": len(requests), "prompt_set_sha256": prompts,
            "settings_observed": {f"{k}={v}": n for (k, v), n in sorted(settings.items())}}


def receipt_gaps(m: dict, root: Path, manifest_path: Path) -> list[dict]:
    gaps = []

    def gap(kind: str, field: str, detail: str) -> None:
        gaps.append({"type": kind, "field": field, "detail": detail})

    normalized_path = root / m["normalized_run"]["uri"]
    is_run = False
    if normalized_path.is_file():
        try:
            data = read_json(normalized_path)
            is_run = isinstance(data, dict) and "dimensions" in data and "native_results" in data
        except (ValueError, OSError):
            pass
    lanes_dir = root / "reference/agentmem_ref/evaluation/lanes"
    lane_ids = {f.stem for f in lanes_dir.glob("*.json")}
    claimed = m["benchmark"]["task_profile"].split(":", 1)[0]
    if claimed in lane_ids:
        lane = json.loads((lanes_dir / f"{claimed}.json").read_text())
        frozen = re.search(r"blob ([0-9a-f]{40})", lane["evaluator"]["scorer"])
        gap("metadata", "benchmark.task_profile",
            f"claims frozen lane {claimed!r} (scorer blob {frozen.group(1)[:12] if frozen else '?'}, runner "
            f"{lane['execution']['environment'].get('runner')}) but this is a self-run outside that lane; "
            "a consumer grouping by task_profile would pool it with accepted lane rows")
    if not is_run:
        gap("metadata", "normalized_run", "points at a runner/evaluator report, not a memory-benchmark-run record; "
            "no normalized run exists for this row")
    if not HEX40.search(m["system"]["adapter_revision"]) and not m["system"]["adapter_revision"].startswith("git-blob:"):
        history = adapter_history(root, m["system"]["adapter_id"])
        if history and history["commits"] == 1:
            gap("metadata", "system.adapter_revision", f"{m['system']['adapter_revision']!r} is a label; the adapter file has one "
                f"commit in history, so its only blob {history['blob']} is recoverable (compare the bundle preregistration)")
        else:
            gap("evidence", "system.adapter_revision", f"{m['system']['adapter_revision']!r} is a label, not an immutable blob or commit")
    if "+" in m["benchmark"]["input_sha256"]:
        gap("metadata", "benchmark.input_sha256", "two file digests joined with '+'; v1 needs one digest: use the frozen AMB "
            "lane's input_sha256 (SHA-256 over the raw fixture bytes in order), which these component digests match")
    kinds = {a["kind"] for a in m["artifacts"]}
    if "native_result" not in kinds:
        gap("metadata", "artifacts", "no artifact typed native_result (native output is present under another kind)")
    if m["costs"]["status"] == "not_measured":
        gap("metadata", "costs", "not_measured; acceptance needs measured or not_applicable (all inference here is local)")
    for call in m["inference"]["calls"]:
        if call["purpose"] not in CALL_PURPOSES:
            gap("metadata", "inference.calls.purpose", f"free text {call['purpose']!r}")
        if call["purpose"] in ("generation", "judge") or call["purpose"] not in CALL_PURPOSES:
            missing = {"temperature", "top_p", "seed", "context_window_tokens", "max_output_tokens"} - set(call["parameters"])
            shim = shim_parameters(manifest_path.parent)
            observed = {k.split("=")[0] for k in (shim or {}).get("settings_observed", {}) if not k.endswith("=null")}
            per_request = {"max_output_tokens": "max_tokens", "top_p": "top_p", "seed": "seed", "temperature": "temperature"}
            if not call["prompt_sha256"]:
                if shim:
                    gap("metadata", "inference.prompt_sha256", f"{call['model_id']}: no prompt digest recorded; the committed "
                        f"{shim['log']} holds all {shim['chat_requests']} request bodies (prompt-set digest "
                        f"{shim['prompt_set_sha256'][:16]}..., per-request digests derivable)")
                else:
                    gap("evidence", "inference.prompt_sha256", f"{call['model_id']}: no prompt digest and no request log")
            aliases = {"context_window_tokens": "n_ctx"}
            for name in sorted(missing):
                if aliases.get(name) in call["parameters"]:
                    gap("metadata", "inference.parameters", f"{call['model_id']}: {name} recorded under "
                        f"{aliases[name]!r} = {call['parameters'][aliases[name]]}; rename")
                elif per_request.get(name) in observed:
                    gap("metadata", "inference.parameters", f"{call['model_id']}: {name} not recorded; observed in {shim['log']}")
                else:
                    gap("evidence", "inference.parameters", f"{call['model_id']}: {name} not recorded and not sent per request; "
                        "only a server start flag or the pinned server's default can establish it")
        if not call["model_revision"] and not call["model_digest"]:
            gap("evidence", "inference.model", f"{call['model_id']}: neither revision nor digest")
    if not m["review"]["reviewer"] or not m["review"]["decision_ref"]:
        gap("governance", "review", "no reviewer or decision reference; no owner review authority record exists")
    if m["review"]["status"] != "accepted":
        gap("governance", "review.status", f"{m['review']['status']}; external rows are accepted only as frozen same-harness lane rows")
    return gaps


def rows_by_question(rows) -> dict:
    return {r["question_id"]: r for r in rows}


def lme_equivalence(root: Path) -> dict:
    """Self-run controls and Mem0 rows vs the accepted lane v6 rows, per question."""
    lane_dir = root / "reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6"
    self_full = read_json(root / "reports/benchmarks/runs/controls/full500/controls-500.json.gz")
    self_mem0 = read_json(root / "reports/benchmarks/runs/mem0/subset50/mem0-50.json.gz")
    out = {}
    for backend, report in (("agent_memory", self_full), ("lexical_overlap", self_full), ("mem0_explicit", self_mem0)):
        for plane in ("session", "turn"):
            lane_file = next(lane_dir.glob(f"{backend}-{plane}-*/report.rows.json.gz"))
            lane = rows_by_question(read_json(lane_file)[plane][backend])
            mine = rows_by_question(report["planes"][plane]["backends"][backend]["rows"])
            shared = sorted(set(lane) & set(mine))
            same_metrics = sum(lane[q]["metrics"] == mine[q]["metrics"] for q in shared)
            same_ranking = sum(lane[q]["ranked_top"] == mine[q]["ranked_top"] for q in shared)
            out[f"{backend}:{plane}"] = {"lane_rows": str(lane_file.relative_to(root)), "questions_compared": len(shared),
                                         "metrics_identical": same_metrics, "ranking_identical": same_ranking}
    return out


def amb_outcomes(path: Path) -> dict:
    return {r["query_id"]: bool(r["correct"]) for r in read_json(path)["results"]}


def amb_repeats(root: Path) -> dict:
    runs = root / "reports/benchmarks/runs"
    out = {}
    for name, bundle in (("hindsight", "640-hindsight"), ("mempalace", "mempalace"), ("graphiti", "812-graphiti")):
        base = runs / bundle / "amb-precisionmembench-single-turn"
        one, two = read_json(base / "rep1/single-turn.json"), read_json(base / "rep2/single-turn.json")
        a, b = ({r["query_id"]: r for r in x["results"]} for x in (one, two))
        out[name] = {"cases": len(a), "correctness_identical": sum(a[q]["correct"] == b[q]["correct"] for q in a),
                     "retrieved_answer_identical": sum(a[q].get("answer") == b[q].get("answer") for q in a),
                     "correct_rep1": sum(bool(r["correct"]) for r in a.values()),
                     "correct_rep2": sum(bool(r["correct"]) for r in b.values())}
    out["langmem"] = {"cases": 77, "repeat": "none (single complete run)"}
    return out


def amb_reference_rows(root: Path) -> dict:
    """Counts of the accepted lane reference rows and of the external rows, and whether the external pass sets coincide."""
    lane = root / "reports/benchmarks/amb/amb-precisionmembench-retrieval-v6"
    refs = {name: amb_outcomes(next(lane.glob(f"{name}-*/single-turn.json"))) for name in ("agent-memory", "bm25", "mem0-explicit")}
    runs = root / "reports/benchmarks/runs"
    external = {
        "hindsight": runs / "640-hindsight/amb-precisionmembench-single-turn/rep1/single-turn.json",
        "mempalace": runs / "mempalace/amb-precisionmembench-single-turn/rep1/single-turn.json",
        "graphiti": runs / "812-graphiti/amb-precisionmembench-single-turn/rep1/single-turn.json",
        "langmem": runs / "813-langmem/amb-precisionmembench-single-turn/rep1/single-turn.json",
    }
    passes = {name: sorted(q for q, ok in amb_outcomes(path).items() if ok) for name, path in external.items()}
    return {"lane": str(lane.relative_to(root)),
            "lane_correct": {k: sum(v.values()) for k, v in refs.items()},
            "external_correct": {k: len(v) for k, v in passes.items()},
            "external_pass_sets_identical": len({tuple(v) for v in passes.values()}) == 1,
            "external_passes_within_bm25_passes": {k: set(v) <= {q for q, ok in refs["bm25"].items() if ok} for k, v in passes.items()}}


COHORT_SOURCES = {
    "agent_memory": "reports/benchmarks/amb/amb-precisionmembench-retrieval-v6/agent-memory-*/single-turn.json",
    "bm25": "reports/benchmarks/amb/amb-precisionmembench-retrieval-v6/bm25-*/single-turn.json",
    "mem0_explicit": "reports/benchmarks/amb/amb-precisionmembench-retrieval-v6/mem0-explicit-*/single-turn.json",
    "mempalace": "reports/benchmarks/runs/mempalace/amb-precisionmembench-single-turn/rep1/single-turn.json",
    "hindsight_chunks": "reports/benchmarks/runs/640-hindsight/amb-precisionmembench-single-turn/rep1/single-turn.json",
    "langmem": "reports/benchmarks/runs/813-langmem/amb-precisionmembench-single-turn/rep1/single-turn.json",
    "graphiti": "reports/benchmarks/runs/812-graphiti/amb-precisionmembench-single-turn/rep1/single-turn.json",
}


def amb_cohort_reproduction(root: Path) -> dict:
    """Rebuild each committed AMB cohort table from accepted lane v6 rows plus the external rep1 rows."""
    out = {}
    for table in sorted((root / "reports/benchmarks/runs").glob("*/amb-precisionmembench-single-turn/paired-vs-cohort.json")):
        committed = read_json(table)
        args = [f"--system={label}={next(root.glob(COHORT_SOURCES[label]))}" for label in committed["systems"]]
        rebuilt = subprocess.run([sys.executable, "-I", str(root / "scripts/paired_amb_systems.py"), *args,
                                  f"--reference={committed['reference']}"], capture_output=True, text=True, check=True)
        out[str(table.relative_to(root))] = {"systems": list(committed["systems"]),
                                             "identical_as_parsed_json": json.loads(rebuilt.stdout) == committed}
    return out


def llm_call_identity(root: Path) -> dict:
    """Graphiti rep1 vs rep2: request bodies, completion texts and raw responses from the committed shim logs."""
    base = root / "reports/benchmarks/runs/812-graphiti/amb-precisionmembench-single-turn"
    logs = []
    for rep in ("rep1", "rep2"):
        lines = gzip.decompress((base / rep / "shim-calls.jsonl.gz").read_bytes()).decode().splitlines()
        logs.append([json.loads(line) for line in lines if line and "request" in json.loads(line)])
    one, two = logs
    pairs = list(zip(one, two))
    text = lambda e: [c["message"].get("content") for c in e["response"]["choices"]]  # noqa: E731
    return {"chat_requests": [len(one), len(two)],
            "requests_identical": sum(a["request"] == b["request"] for a, b in pairs),
            "completion_texts_identical": sum(text(a) == text(b) for a, b in pairs),
            "raw_responses_identical": sum(a["response"] == b["response"] for a, b in pairs),
            "note": "raw responses carry per-call ids and timestamps, so 'content-identical' is the accurate term"}


GOLD_KEYS = {"answer", "answer_session_ids", "has_answer", "gold", "expected", "shouldOnlyInclude", "shouldInclude",
             "shouldExclude", "category", "question_type", "relevant", "relevant_ids", "meta", "noans", "evidence",
             "answer_turn_ids"}


def gold_key_reads(root: Path) -> dict:
    """String-keyed subscripts, .get() keys and attributes naming a gold field, per bridge/worker/runner file."""
    files = sorted({*root.glob("reference/longmemeval_*_bridge.py"), *root.glob("reference/amb_*_bridge.py"),
                    *root.glob("reference/*_amb_worker.py"), root / "reference/run_amb_external.py",
                    root / "reference/run_longmemeval_resumable.py"})
    out = {}
    for path in files:
        hits = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value in GOLD_KEYS:
                hits.add(node.slice.value)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                    and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in GOLD_KEYS):
                hits.add(node.args[0].value)
            if isinstance(node, ast.Attribute) and node.attr in GOLD_KEYS:
                hits.add("." + node.attr)
        out[str(path.relative_to(root))] = sorted(hits)
    return out


def lme_denominators(root: Path) -> dict:
    out = {}
    for bundle, backend in (("640-hindsight/full500", "hindsight_chunks_onnx"), ("mempalace/full500", "mempalace_default_local")):
        for plane in ("session", "turn"):
            base = root / "reports/benchmarks/runs" / bundle
            summary = read_json(base / f"{plane}.{backend}.summary.json")
            rows = [json.loads(line) for line in (base / f"{plane}.{backend}.rows.jsonl").read_text().splitlines() if line]
            agg = summary["aggregate"]
            out[f"{backend}:{plane}"] = {
                "rows": len(rows), "distinct_questions": len({r["question_id"] for r in rows}),
                "scored": agg["evaluated_question_count"],
                "excluded": agg["excluded_abstention_count"] + agg["excluded_no_user_target_count"],
                "row_status": dict(Counter(r["status"] for r in rows)),
                "runtime_errors": sum(bool(r.get("runtime_error")) for r in rows),
                "failures": summary["failures"],
                "max_returned": max(r["returned_count"] for r in rows),
            }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence-root", type=Path, required=True, help="checkout of the evidence commit")
    parser.add_argument("--evidence-commit", required=True)
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    validator = load_validator()
    manifests = sorted((root / "reports/benchmarks/runs").glob("**/*manifest.json"))
    report = {
        "evidence_commit": args.evidence_commit,
        "manifests": [audit_manifest(validator, root, path) for path in manifests],
        "cross_checks": {
            "longmemeval_self_run_vs_accepted_lane_v6": lme_equivalence(root),
            "longmemeval_denominators": lme_denominators(root),
            "amb_repeats": amb_repeats(root),
            "amb_reference_rows": amb_reference_rows(root),
            "amb_cohort_tables_rebuilt": amb_cohort_reproduction(root),
            "graphiti_llm_calls_rep1_vs_rep2": llm_call_identity(root),
            "gold_key_reads": gold_key_reads(root),
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
