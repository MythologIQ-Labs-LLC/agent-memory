#!/usr/bin/env bash
# Local, workflow-equivalent execution of one row of the frozen AMB PrecisionMemBench retrieval lane.
# Mirrors .github/workflows/amb-competitive.yml (retrieval mode, full selection) and lays the artifact
# out as `gh run download` would. usage: run_amb_row.sh <memory> <run_id>
set -euo pipefail
MEMORY="$1"; RUN_ID="$2"
REPO=/home/user/agent-memory
B=/tmp/claude-0/-home-user-agent-memory/d41e5087-c642-5965-a920-d612859a1976/scratchpad/bench
VENV=${AMB_VENV:-$B/venv312}
PY=$VENV/bin/python
AMB_ROOT=$B/external/amb
CONSTRAINTS=${AMB_CONSTRAINTS:-$B/amb-constraints.txt}
PROVENANCE=${AMB_CONSTRAINTS_PROVENANCE:-$B/amb-constraints-provenance.json}
AMB_REVISION=03c1d0f1d27da63034f0931121c858faba512383
LANE_ID=amb-precisionmembench-retrieval-v7
LANE_FILE=reference/agentmem_ref/evaluation/lanes/$LANE_ID.json
SHA="$(git -C $REPO rev-parse HEAD)"
OUT=$B/runs-691/amb/$RUN_ID/amb-$LANE_ID-precisionmembench-single-turn-$MEMORY-$SHA
mkdir -p "$OUT"
cd "$REPO"
# Tracked files must be clean (the executing revision is HEAD); untracked files are tolerated only
# under reports/benchmarks/ (imported evidence of earlier rows, which no execution path reads).
test "$(git status --porcelain --untracked-files=no | wc -l)" = "0" || { echo "dirty tree" >&2; exit 2; }
test "$(git status --porcelain | grep -vE '^\?\? reports/' | wc -l)" = "0" || { echo "untracked files outside reports/" >&2; exit 2; }
# The session's network policy denies openaipublic.blob.core.windows.net, from which tiktoken fetches
# cl100k_base.tiktoken (used by the harness only for context token counts). litellm==1.82.1, a locked
# dependency of the frozen harness, vendors that exact file (tiktoken verifies its pinned sha256
# 223921b7… before use) and itself points TIKTOKEN_CACHE_DIR at this directory whenever imported.
export TIKTOKEN_CACHE_DIR="$($PY -c 'import litellm.litellm_core_utils.default_encoding as d, os; print(os.environ["TIKTOKEN_CACHE_DIR"])' 2>/dev/null)"
test -n "$TIKTOKEN_CACHE_DIR"
export TIKTOKEN_CL100K_SHA256="$(sha256sum "$TIKTOKEN_CACHE_DIR/9b5ad71b2ce5302211f9c61530b329a4922fc6a4" | cut -c1-64)"
test "$TIKTOKEN_CL100K_SHA256" = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
test -z "${AMB_PMB_RETURN_CAP:-}"
export GEMINI_API_KEY=retrieval-only-unused GOOGLE_API_KEY=retrieval-only-unused MEM0_TELEMETRY=false HF_HOME=$B/hf-home
export PRECISIONMEMBENCH_DATA_PATH=$B/inputs/pmb-fixtures
# Workflow job env: frozen AMB constructs its configured answer client even in RetrievalMode
# (never called); the key above is the workflow's inert placeholder, not a credential.
export OMB_ANSWER_LLM=gemini OMB_ANSWER_MODEL=gemini-2.5-flash-lite OMB_JUDGE_LLM=gemini OMB_JUDGE_MODEL=gemini-2.5-flash-lite

test "$(git -C $AMB_ROOT rev-parse HEAD)" = "$AMB_REVISION"
PYTHONPATH=reference $PY - <<PY
import sys
sys.path.insert(0, "reference")
from amb_agent_memory_bridge import verify_amb_checkout
print(verify_amb_checkout("$AMB_ROOT"))
PY

line="$($PY scripts/check_runtime_baseline_equivalence.py --candidate HEAD 2>&1 || true)"
state="$(echo "$line" | grep -oE 'equivalence: [A-Z]+' | head -n1 | cut -d' ' -f2 || true)"; state="${state:-FAIL}"
declaration="$(git hash-object reports/runtime/baseline-v7-declaration.json)"
export RUNTIME_BASELINE_STATE="$state" RUNTIME_BASELINE_LINE="$line" DECLARATION_BLOB="$declaration"

LANE_CLI=$VENV/bin/agent-memory; test -x "$LANE_CLI" || LANE_CLI=$B/venv312/bin/agent-memory
"$LANE_CLI" benchmark validate-lane "$LANE_FILE" --json > "$OUT/lane-validation.json"
test -s "$OUT/lane-validation.json"
LANE_FILE="$LANE_FILE" MEMORY="$MEMORY" AMB_REVISION="$AMB_REVISION" $PY - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path
lane = json.loads(Path(os.environ["LANE_FILE"]).read_text(encoding="utf-8"))
assert lane["status"] == "frozen", lane["status"]
assert lane["harness"]["revision"] == os.environ["AMB_REVISION"]
row = next(item for item in lane["systems"] if item["provider_key"] == os.environ["MEMORY"])
assert row["status"] == "frozen", (row["row_id"], row["status"], row.get("status_reason"))
for path, blob in lane["harness"]["source_blobs"].items():
    if not path.startswith("reference/"):
        continue
    actual = subprocess.run(["git", "hash-object", path], capture_output=True, text=True, check=True).stdout.strip()
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
PYTHONPATH=reference $PY reference/run_amb_external.py --amb-root $AMB_ROOT -- "${args[@]}" 2>&1 | tee "$OUT/run.log"
end=$(date -u +%s)
echo "elapsed_s $((end-start))" | tee -a "$OUT/run.log"

cp "$CONSTRAINTS" "$OUT/amb-constraints.txt"; cp "$PROVENANCE" "$OUT/amb-constraints-provenance.json"
LANE_FILE="$LANE_FILE" MEMORY="$MEMORY" AMB_REVISION="$AMB_REVISION" RUN_ID="$RUN_ID" SHA="$SHA" OUT="$OUT" $PY - <<'PY'
import importlib.metadata as md, importlib.util, json, os, platform, subprocess
from pathlib import Path
def version(name):
    try: return md.version(name)
    except md.PackageNotFoundError: return None
def blob(path):
    return subprocess.run(["git", "hash-object", path], capture_output=True, text=True, check=True).stdout.strip()
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
    "bridge_blobs": {"reference/amb_agent_memory_bridge.py": blob("reference/amb_agent_memory_bridge.py"),
                     "reference/amb_mem0_explicit_bridge.py": blob("reference/amb_mem0_explicit_bridge.py")},
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
    },
}
(out / "execution-identity.json").write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: identity[k] for k in ("agent_memory_revision", "runtime_baseline_state", "declaration_blob", "lane_digest_sha256", "resolved_packages")}, indent=1))
PY
cd "$OUT" && find . -type f -print | sort > files.txt && while IFS= read -r file; do sha256sum "$file"; done < files.txt > sha256.txt
echo "DONE $MEMORY -> $OUT"
