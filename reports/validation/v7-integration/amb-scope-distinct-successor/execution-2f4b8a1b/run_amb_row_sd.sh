#!/usr/bin/env bash
# Local, workflow-equivalent execution of one row of the frozen scope-distinct successor AMB lane
# (amb-precisionmembench-retrieval-v7-scope-distinct-v1). Mirrors .github/workflows/amb-competitive.yml
# for that lane_id: successor LANE_FILE, raw-byte source blob checks, run_amb_external_scope_distinct.py,
# bridge_blobs from the lane source_blobs. Lays the artifact out as `gh run download` would.
# usage: run_amb_row_sd.sh <memory> <run_id>
set -euo pipefail
MEMORY="$1"; RUN_ID="$2"
S=/tmp/claude-0/-home-user-agent-memory/df091f7c-0b03-5d12-806d-4c56a896fc2c/scratchpad
REPO=$S/lane-wt
B=$S/bench/sd
VENV=${AMB_VENV:-$B/venv312}
PY=$VENV/bin/python
AMB_ROOT=$S/lane-inputs/amb-harness
CONSTRAINTS=$B/c-$MEMORY.txt
PROVENANCE=$B/p-$MEMORY.json
AMB_REVISION=03c1d0f1d27da63034f0931121c858faba512383
LANE_ID=amb-precisionmembench-retrieval-v7-scope-distinct-v1
LANE_FILE=reports/validation/v7-integration/amb-scope-distinct-successor/$LANE_ID.json
RUNNER=reference/run_amb_external_scope_distinct.py
SHA="$(git -C $REPO rev-parse HEAD)"
OUT=$B/runs/$RUN_ID/amb-$LANE_ID-precisionmembench-single-turn-$MEMORY-$SHA
mkdir -p "$OUT"
cd "$REPO"
test "$(git status --porcelain | wc -l)" = "0" || { echo "dirty tree" >&2; exit 2; }
# tiktoken: litellm==1.82.1 (locked harness dependency) vendors cl100k_base; the network policy denies
# openaipublic.blob.core.windows.net. tiktoken verifies the pinned sha256 before use.
export TIKTOKEN_CACHE_DIR="$($PY -c 'import litellm.litellm_core_utils.default_encoding as d, os; print(os.environ["TIKTOKEN_CACHE_DIR"])' 2>/dev/null)"
test -n "$TIKTOKEN_CACHE_DIR"
export TIKTOKEN_CL100K_SHA256="$(sha256sum "$TIKTOKEN_CACHE_DIR/9b5ad71b2ce5302211f9c61530b329a4922fc6a4" | cut -c1-64)"
test "$TIKTOKEN_CL100K_SHA256" = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
test -z "${AMB_PMB_RETURN_CAP:-}"
export GEMINI_API_KEY=retrieval-only-unused GOOGLE_API_KEY=retrieval-only-unused MEM0_TELEMETRY=false HF_HOME=$S/bench/hf-home
export PRECISIONMEMBENCH_DATA_PATH=$S/lane-inputs/pmb
export OMB_ANSWER_LLM=gemini OMB_ANSWER_MODEL=gemini-2.5-flash-lite OMB_JUDGE_LLM=gemini OMB_JUDGE_MODEL=gemini-2.5-flash-lite

if [ "$MEMORY" = "mem0-explicit" ]; then
  $PY - <<'PY'
import importlib.util, json, mem0
assert mem0.__version__ == "2.2.1", mem0.__version__
posture = {"mem0ai": mem0.__version__, "fastembed_installed": importlib.util.find_spec("fastembed") is not None,
           "spacy_installed": importlib.util.find_spec("spacy") is not None}
assert posture["fastembed_installed"] is False and posture["spacy_installed"] is False, posture
print(json.dumps(posture))
PY
fi
test "$(git -C $AMB_ROOT rev-parse HEAD)" = "$AMB_REVISION"
$PY - <<PY
import sys
sys.path.insert(0, "reference")
from amb_agent_memory_bridge import verify_amb_checkout
print(verify_amb_checkout("$AMB_ROOT"))
PY

line="$($PY scripts/check_runtime_baseline_equivalence.py --candidate HEAD)"
state="$(echo "$line" | grep -oE 'equivalence: [A-Z]+' | head -n1 | cut -d' ' -f2)"
declaration="$(git hash-object reports/runtime/baseline-v7-declaration.json)"
export RUNTIME_BASELINE_STATE="$state" RUNTIME_BASELINE_LINE="$line" DECLARATION_BLOB="$declaration"
echo "runtime baseline: $line"

$VENV/bin/agent-memory benchmark validate-lane "$LANE_FILE" --json > "$OUT/lane-validation.json"
test -s "$OUT/lane-validation.json"
LANE_FILE="$LANE_FILE" MEMORY="$MEMORY" AMB_REVISION="$AMB_REVISION" LANE_ID="$LANE_ID" $PY - <<'PY'
import hashlib, json, os
from pathlib import Path
lane = json.loads(Path(os.environ["LANE_FILE"]).read_text(encoding="utf-8"))
assert lane["status"] == "frozen", lane["status"]
assert lane["lane_id"] == os.environ["LANE_ID"]
assert lane["harness"]["revision"] == os.environ["AMB_REVISION"]
row = next(item for item in lane["systems"] if item["provider_key"] == os.environ["MEMORY"])
assert row["status"] == "frozen", (row["row_id"], row["status"], row.get("status_reason"))
for path, blob in lane["harness"]["source_blobs"].items():
    if not path.startswith("reference/"):
        continue
    data = Path(path).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data).hexdigest()
    assert actual == blob, (path, actual, blob)
    print(f"{path} blob {actual}: frozen")
combined = hashlib.sha256()
for fixture in lane["dataset"]["fixtures"]:
    payload = (Path(os.environ["PRECISIONMEMBENCH_DATA_PATH"]) / fixture["name"]).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert digest == fixture["sha256"], (fixture["name"], digest, fixture["sha256"])
    combined.update(payload)
    print(f"fixture {fixture['name']} sha256 {digest}: frozen")
assert combined.hexdigest() == lane["dataset"]["input_sha256"], combined.hexdigest()
print(f"input_sha256 {combined.hexdigest()}: frozen")
PY
(cd $AMB_ROOT && $PY scripts/precisionmembench_selfcheck.py) | tee "$OUT/precisionmembench-selfcheck.txt"

args=(run --dataset precisionmembench --split single-turn --memory "$MEMORY" --mode retrieval --output-dir "$OUT" --name "$MEMORY-${SHA:0:12}")
if [ "$MEMORY" = "agent-memory" ]; then
  export AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR="$OUT/cross-fact.jsonl"
fi
start=$(date -u +%s)
PYTHONPATH=reference $PY "$RUNNER" --amb-root $AMB_ROOT -- "${args[@]}" 2>&1 | tee "$OUT/run.log"
end=$(date -u +%s)
echo "elapsed_s $((end-start))" | tee -a "$OUT/run.log"

cp "$CONSTRAINTS" "$OUT/amb-constraints.txt"; cp "$PROVENANCE" "$OUT/amb-constraints-provenance.json"
LANE_FILE="$LANE_FILE" MEMORY="$MEMORY" AMB_REVISION="$AMB_REVISION" RUN_ID="$RUN_ID" SHA="$SHA" OUT="$OUT" $PY - <<'PY'
import hashlib, importlib.metadata as md, importlib.util, json, os, platform
from pathlib import Path
def version(name):
    try: return md.version(name)
    except md.PackageNotFoundError: return None
def raw_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data).hexdigest()
lane = json.loads(Path(os.environ["LANE_FILE"]).read_text(encoding="utf-8"))
out = Path(os.environ["OUT"])
validation = json.loads((out / "lane-validation.json").read_text(encoding="utf-8"))
harness_constraints = json.loads((out / "amb-constraints-provenance.json").read_text(encoding="utf-8"))
identity = {
    "evidence_class": "same_harness_external_candidate",
    "agent_memory_revision": os.environ["SHA"], "amb_revision": os.environ["AMB_REVISION"],
    "dataset": "precisionmembench", "split": "single-turn", "memory": os.environ["MEMORY"], "mode": "retrieval",
    "query_limit": "0", "answer_model": None, "judge_model": None,
    "lane_id": lane["lane_id"], "lane_file": os.environ["LANE_FILE"],
    "lane_digest_sha256": validation.get("lane_digest_sha256"),
    "runtime_baseline_state": os.environ.get("RUNTIME_BASELINE_STATE"),
    "runtime_baseline_line": os.environ.get("RUNTIME_BASELINE_LINE"),
    "declaration_blob": os.environ.get("DECLARATION_BLOB") or None,
    "full_selection": True, "amb_pmb_return_cap": os.environ.get("AMB_PMB_RETURN_CAP"),
    "bridge_blobs": {path: raw_blob(path) for path in lane["harness"]["source_blobs"] if path.startswith("reference/")},
    "resolved_packages": {name: version(name) for name in ("mem0ai", "qdrant-client", "sentence-transformers", "torch", "rank-bm25", "openai", "sqlalchemy", "posthog", "hindsight-all", "hindsight-client", "uv")},
    "harness_constraints": harness_constraints,
    "mem0_optional_components": {"fastembed_installed": importlib.util.find_spec("fastembed") is not None, "spacy_installed": importlib.util.find_spec("spacy") is not None},
    "runner": f"local cloud container, {platform.platform()}, Python {platform.python_version()} (not a GitHub-hosted runner)",
    "workflow_run_id": os.environ["RUN_ID"],
    "authority_effect": "none",
    "local_execution_notes": {
        "tiktoken_cl100k_base_source": "litellm==1.82.1 vendored copy (locked harness dependency); TIKTOKEN_CACHE_DIR=" + os.environ["TIKTOKEN_CACHE_DIR"],
        "tiktoken_cl100k_base_sha256": os.environ["TIKTOKEN_CL100K_SHA256"],
        "tiktoken_cl100k_base_reason": "session network policy denies openaipublic.blob.core.windows.net; tiktoken verifies the same pinned sha256 before use",
        "venv": os.environ.get("AMB_VENV_LABEL", "venv312"),
        "precisionmembench_fixtures": "pre-downloaded from the lane fixture URLs; sha256 re-verified above and re-fetched by the importer",
    },
}
(out / "execution-identity.json").write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: identity[k] for k in ("agent_memory_revision", "runtime_baseline_state", "declaration_blob", "lane_digest_sha256", "bridge_blobs")}, indent=1))
PY
cd "$OUT" && find . -type f -print | sort > files.txt && while IFS= read -r file; do sha256sum "$file"; done < files.txt > sha256.txt
echo "DONE $MEMORY -> $OUT"
