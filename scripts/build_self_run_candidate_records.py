#!/usr/bin/env python3
"""Build superseding self-run records for the 21 audited execution manifests (#808).

Read-only on the originals and on all raw evidence. For each
``reports/benchmarks/runs/**/*manifest.json`` under ``--evidence-root`` this writes one record
under ``reports/benchmarks/self-run-candidates/`` (same relative path) that:

* carries ``candidate_class``: class, tier, system variant, what it is *not* equivalent to,
  ``metric_record: native_report``, the superseded manifest's path and SHA-256, and one
  correction entry (JSON pointer, original value, corrected value, basis) per changed field;
* fixes only metadata that committed evidence (or the pinned server source) determines:
  pointer base, the AMB lane input digest, a ``self-run:`` run id and task profile that no
  longer name a frozen lane, ``native_result`` typing, blob-pinned adapter revisions, inference
  settings and token counts from the committed shim logs, ``not_applicable`` cost for unbilled
  local inference, and an honest ``redaction.reviewed: false``.

No value is measured anew and no raw file is modified. Every record is then validated in
re-hash mode, including the supersession trail. ``--check`` compares instead of writing.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = "reports/benchmarks/self-run-candidates"
LME_RUNNER_PROFILE = "agent-memory-longmemeval-retrieval-currentness-v1"
TOP_P_BASIS = ("not sent per request; pinned llama-cpp-python 0.3.16 server default for /v1/chat/completions "
               "(llama_cpp/server/types.py top_p_field default=0.95; file sha256 a6c5b3b8... equals the wheel RECORD)")
MAX_TOKENS_BASIS = ("not sent per request; pinned llama-cpp-python 0.3.16 chat default max_tokens=None, i.e. "
                    "bounded only by n_ctx (llama_cpp/server/types.py)")
LANE_BASELINE = "frozen same-harness lane rows (official benchmark lanes)"
ABSENT = "<absent>"

# Classification from RECEIPT-AUDIT.md section 4; variants and non-equivalences travel with each row.
CLASSES = [
    ("640-hindsight/full500/", "self_run_candidate",
     "Hindsight 0.10.2 chunk-only (llm_provider=none): local ONNX e5-small dense + text search fused by RRF; "
     "graph, temporal, observation and rerank arms off",
     ["Hindsight's LLM-enabled product", "Hindsight published benchmark figures", LANE_BASELINE]),
    ("640-hindsight/amb-", "self_run_candidate",
     "Hindsight 0.10.2 chunk-only (llm_provider=none), AMB protocol A, no timestamps supplied",
     ["Hindsight's LLM-enabled product", "AMB published Hindsight figure (LLM ingestion plus filters)", LANE_BASELINE]),
    ("640-hindsight/subset50/", "self_run_diagnostic",
     "Hindsight 0.10.2 chunk-only, 50-question subset used for the host-variance probe (superseded by full 500)",
     ["Hindsight's LLM-enabled product", LANE_BASELINE]),
    ("mempalace/full500/", "self_run_candidate",
     "MemPalace 3.11.0 defaults through its own MCP tools: ChromaDB with local MiniLM, BM25 hybrid re-rank; "
     "executed in two segments",
     ["MemPalace published raw-ChromaDB benchmark figure", LANE_BASELINE]),
    ("mempalace/amb-", "self_run_candidate",
     "MemPalace 3.11.0 defaults, AMB protocol A, no timestamps supplied",
     ["MemPalace published benchmark figures", LANE_BASELINE]),
    ("812-graphiti/", "self_run_candidate",
     "Graphiti 0.31.1 (graphiti-core[falkordblite]) with local Qwen2.5-3B-Instruct Q4_K_M at temperature 0 and "
     "nomic-embed-text v1.5; AMB protocol A",
     ["Zep's hosted product", "Graphiti with a frontier LLM", LANE_BASELINE]),
    ("813-langmem/", "self_run_not_comparable",
     "LangMem 0.0.30 with local Qwen2.5-3B-Instruct Q4_K_M tool calling; 4 memories written from 35 documents",
     ["a LangMem measurement (the 3B model's tool calling dominates)", "LangMem with its documented hosted models",
      LANE_BASELINE]),
    ("mem0/subset50/", "self_run_diagnostic",
     "Mem0 OSS 2.2.1 explicit (infer=False), 50-question reproduction check of the accepted lane row",
     ["the accepted Mem0 lane row (that row remains authoritative)", "Mem0 reflective (LLM) extraction"]),
    ("controls/", "self_run_diagnostic",
     "self-run Agent Memory / lexical-overlap harness-equivalence control",
     ["the accepted Agent Memory and lexical-overlap lane rows (those remain the baseline)"]),
]


def load_validator():
    spec = importlib.util.spec_from_file_location("execution_manifest_validator",
                                                  REPO / "scripts/validate_benchmark_execution_manifest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(root: Path, manifest_path: Path, uri: str) -> str:
    """Repository-root form of a pointer written relative to the root, the manifest or the bundle."""
    for base in (root, manifest_path.parent, manifest_path.parent.parent):
        candidate = (base / uri).resolve()
        if candidate.is_file() and root in candidate.parents:
            return candidate.relative_to(root).as_posix()
    raise ValueError(f"{manifest_path}: pointer {uri!r} does not resolve")


def git_blob(root: Path, path: str) -> str:
    return subprocess.run(["git", "-C", str(root), "rev-parse", f"HEAD:{path}"],
                          capture_output=True, text=True, check=True).stdout.strip()


def lane_input_digest(components: list[str]) -> tuple[str, str]:
    for lane_file in sorted((REPO / "reference/agentmem_ref/evaluation/lanes").glob("*.json")):
        dataset = json.loads(lane_file.read_text(encoding="utf-8")).get("dataset", {})
        if [f.get("sha256") for f in dataset.get("fixtures", [])] == components and dataset.get("input_sha256"):
            return dataset["input_sha256"], lane_file.stem
    raise ValueError("no frozen lane matches the component input digests")


def shim_summary(bundle: Path) -> dict:
    lines = gzip.decompress((bundle / "shim-calls.jsonl.gz").read_bytes()).decode().splitlines()
    chat = [json.loads(line) for line in lines if line and "request" in json.loads(line)]
    observed = {key: sorted({json.dumps(c["request"][key]) if key in c["request"] else "not sent" for c in chat})
                for key in ("max_tokens", "top_p", "seed")}
    return {
        "requests": len(chat),
        "prompt_set_sha256": hashlib.sha256(json.dumps([c["request"].get("messages") for c in chat], sort_keys=True,
                                                       separators=(",", ":")).encode()).hexdigest(),
        "prompt_tokens": sum(c["response"].get("usage", {}).get("prompt_tokens", 0) for c in chat),
        "completion_tokens": sum(c["response"].get("usage", {}).get("completion_tokens", 0) for c in chat),
        "observed": observed,
    }


def tier_of(calls: list[dict]) -> str:
    if not calls:
        return "no_model"
    if any(c["endpoint_class"] == "hosted" for c in calls):
        return "hosted_model"
    if any(c["purpose"] == "generation" for c in calls):
        return "local_llm_ingestion"
    return "local_embedding_model"


class Record:
    def __init__(self, original: dict):
        self.original, self.doc, self.corrections = original, copy.deepcopy(original), []

    def set(self, pointer: str, value, basis: str) -> None:
        """Set (or, with ABSENT, delete) one field and record the correction; no-op when unchanged."""
        parts = pointer.lstrip("/").split("/")
        node = self.doc
        for part in parts[:-1]:
            node = node[int(part)] if isinstance(node, list) else node[part]
        key = int(parts[-1]) if isinstance(node, list) else parts[-1]
        old = node[key] if (isinstance(node, list) or key in node) else ABSENT
        if old == value:
            return
        if value == ABSENT:
            del node[key]
        else:
            node[key] = value
        self.corrections.append({"pointer": pointer, "original": old, "corrected": value, "basis": basis})


def build_one(root: Path, path: Path) -> tuple[str, dict]:
    rel = path.relative_to(root).as_posix()
    under_runs = rel.split("reports/benchmarks/runs/", 1)[1]
    original = json.loads(path.read_bytes())
    klass, variant, not_equivalent = next((c, v, n) for prefix, c, v, n in CLASSES if under_runs.startswith(prefix))
    record = Record(original)
    doc = record.doc

    # R1/R2 pointer base; R5 native_result typing.
    rebase = "R1/R2: rebased to repository root; digest unchanged"
    normalized_uri = resolve(root, path, original["normalized_run"]["uri"])
    record.set("/normalized_run/uri", normalized_uri, rebase)
    for index, artifact in enumerate(original["artifacts"]):
        uri = resolve(root, path, artifact["uri"])
        record.set(f"/artifacts/{index}/uri", uri, rebase)
        if artifact["kind"] == "evaluator_report" or (uri == normalized_uri and artifact["kind"] == "row_level_results"):
            record.set(f"/artifacts/{index}/kind", "native_result", "R5: native report")

    # R3 AMB input digest: the frozen lane's own rule and value.
    digest = original["benchmark"]["input_sha256"]
    if "+" in digest:
        value, lane = lane_input_digest(digest.split("+"))
        record.set("/benchmark/input_sha256", value, f"R3: components equal the {lane} fixtures in order; "
                   "that lane's input_digest_rule value")

    # R9 self-run identity that names no frozen lane.
    profile = original["benchmark"]["task_profile"]
    if original["benchmark"]["id"].startswith("longmemeval"):
        plane = profile.rsplit(":", 1)[1]
        backend = Path(rel).name.split(".")[1] if Path(rel).name.count(".") >= 3 else original["system"]["id"]
        new_profile = f"self-run:{LME_RUNNER_PROFILE}:{plane}"
        bundle = under_runs.split("/")[0] + ":" + under_runs.split("/")[1]
        new_run_id = f"self-run:{bundle}:{plane}:{backend}"
    else:
        new_profile = f"self-run:{profile}"
        new_run_id = f"self-run:{original['run_id']}"
    record.set("/benchmark/task_profile", new_profile, "R9: self-run outside any frozen lane; runner's own profile")
    record.set("/run_id", new_run_id, "R9: self-run: prefix")

    # R7 adapter blob for label-only revisions (single-commit history verified by the audit).
    if original["system"]["adapter_revision"] == "0.1.0-candidate":
        record.set("/system/adapter_revision", "git-blob:" + git_blob(root, original["system"]["adapter_id"]),
                   "R7: the adapter file's only blob (single-commit history)")

    # R4/R8 inference settings from the committed shim log and the pinned server source.
    bundle_dir = path.parent
    shim = shim_summary(bundle_dir) if (bundle_dir / "shim-calls.jsonl.gz").is_file() else None
    for index, call in enumerate(original["inference"]["calls"]):
        if call["purpose"] in ("generation", "embedding", "judge", "rerank", "other"):
            continue
        base = f"/inference/calls/{index}"
        record.set(f"{base}/purpose", "generation", "R4: v1 enum")
        record.set(f"{base}/parameters/n_ctx", ABSENT, "R8: renamed context_window_tokens")
        record.set(f"{base}/parameters/context_window_tokens", call["parameters"]["n_ctx"],
                   "R8: server flag n_ctx (serving-start-llm.sh)")
        observed_max = shim["observed"]["max_tokens"]
        if observed_max == ["not sent"]:
            value, basis = None, (f"R8: not sent in any of {shim['requests']} logged requests; "
                                  + MAX_TOKENS_BASIS.removeprefix("not sent per request; "))
        elif len(observed_max) == 1:
            value, basis = json.loads(observed_max[0]), f"R8: sent as {observed_max[0]} in all {shim['requests']} logged requests"
        else:
            raise ValueError(f"{rel}: max_tokens varies across requests: {observed_max}")
        record.set(f"{base}/parameters/max_output_tokens", value, basis)
        if shim["observed"]["top_p"] != ["not sent"]:
            raise ValueError(f"{rel}: top_p was sent per request; record the observed value instead of the default")
        record.set(f"{base}/parameters/top_p", 0.95, "R8: " + TOP_P_BASIS)
        record.set(f"{base}/prompt_sha256", shim["prompt_set_sha256"], "R8: prompt-set digest of shim-calls.jsonl.gz")

    # R6 costs: unbilled local inference; tokens from the shim log where one exists.
    record.set("/costs/status", "not_applicable", "R6: no billed inference")
    if shim:
        tokens = "R6: chat-completion usage summed from shim-calls.jsonl.gz (embedding usage excluded)"
        record.set("/costs/input_tokens", shim["prompt_tokens"], tokens)
        record.set("/costs/output_tokens", shim["completion_tokens"], tokens)

    # R11 redaction review was an executor self-declaration.
    record.set("/redaction/reviewed", False, "R11: executor self-check; independent review pending")

    # Review block: class eligibility; correct the audit-identified wording element-wise.
    for index, item in enumerate(original["review"]["limitations"]):
        record.set(f"/review/limitations/{index}", item.replace(
            "byte-identical LLM requests/completions", "content-identical LLM requests and completion texts"),
            "RECEIPT-AUDIT.md: raw responses differ in per-call ids")
    record.set("/review/comparison_eligibility",
               "not_assessed" if klass == "self_run_candidate" else "not_comparable", "class rule")

    doc["candidate_class"] = {
        "class": klass,
        "tier": tier_of(doc["inference"]["calls"]),
        "system_variant": variant,
        "not_equivalent_to": not_equivalent,
        "metric_record": "native_report",
        "supersedes": [{"uri": rel, "sha256": sha256(path)}],
        "corrections": record.corrections,
    }
    return f"{OUT}/{under_runs}", doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="compare with committed records instead of writing")
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    validator = load_validator()
    originals = sorted((root / "reports/benchmarks/runs").glob("**/*manifest.json"))
    problems, summary = [], []
    for path in originals:
        out_rel, doc = build_one(root, path)
        payload = (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        target = root / out_rel
        if args.check:
            if not target.is_file() or target.read_bytes() != payload:
                problems.append(f"stale or missing: {out_rel}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        try:
            validator.validate(json.loads(payload), evidence_root=root, manifest_uri=out_rel)
        except Exception as exc:  # noqa: BLE001 - reported per record
            problems.append(f"{out_rel}: {exc}")
        summary.append({"record": out_rel, "class": doc["candidate_class"]["class"], "tier": doc["candidate_class"]["tier"],
                        "corrections": len(doc["candidate_class"]["corrections"])})
    print(json.dumps({"records": summary, "problems": problems}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
