#!/usr/bin/env bash
# Local, workflow-equivalent execution of one (backend, plane) row of the frozen LongMemEval_S lane.
# Mirrors .github/workflows/longmemeval-competitive.yml step by step and lays the artifact out as
# `gh run download` would (<runs-dir>/<run_id>/<artifact-name>/...), so the repository importer can
# bind it. usage: run_lme_row.sh <backend> <plane> <run_id>
set -euo pipefail
BACKEND="$1"; PLANE="$2"; RUN_ID="$3"
REPO=/tmp/claude-0/-home-user-agent-memory/df091f7c-0b03-5d12-806d-4c56a896fc2c/scratchpad/lane-wt
B=/tmp/claude-0/-home-user-agent-memory/df091f7c-0b03-5d12-806d-4c56a896fc2c/scratchpad/bench
LME_VENV=${LME_VENV:-$B/venv312-lme}
PY=$LME_VENV/bin/python
# Workflow job env (longmemeval-competitive.yml): MEM0_TELEMETRY, HF_HOME (local path)
export MEM0_TELEMETRY=false HF_HOME=$B/lme-hf-home
LANE_ID=longmemeval-s-retrieval-parity-v7
LANE_FILE=reference/agentmem_ref/evaluation/lanes/$LANE_ID.json
INPUT=/tmp/claude-0/-home-user-agent-memory/df091f7c-0b03-5d12-806d-4c56a896fc2c/scratchpad/lane-inputs/lme/longmemeval_s_cleaned.json
SHA="$(git -C $REPO rev-parse HEAD)"
OUT=$B/runs/lme/$RUN_ID/longmemeval-lane-$LANE_ID-$BACKEND-$PLANE-$SHA
mkdir -p "$OUT"
cd "$REPO"
export PYTHONPATH=reference
test "$(git status --porcelain | wc -l)" = "0" || { echo "dirty tree" >&2; exit 2; }

# Runtime Baseline posture
line="$($PY scripts/check_runtime_baseline_equivalence.py --candidate HEAD)"
state="$(echo "$line" | grep -oE 'equivalence: [A-Z]+' | head -n1 | cut -d' ' -f2)"
declaration="$(git hash-object reports/runtime/baseline-v7-declaration.json)"
export RUNTIME_BASELINE_STATE="$state" RUNTIME_BASELINE_LINE="$line" DECLARATION_BLOB="$declaration"

# Workflow step "Install the frozen Mem0 OSS row" (verification half; the pins were installed
# into $LME_VENV with the workflow's exact MEM0_PINS when the venv was built)
if [ "$BACKEND" = "mem0_explicit" ]; then
  $PY - <<'PY'
import json
from longmemeval_mem0_explicit_bridge import verify_install_posture
print(json.dumps(verify_install_posture()))
PY
fi

# Lane and blob verification
$LME_VENV/bin/agent-memory benchmark validate-lane "$LANE_FILE" --json > "$OUT/lane-validation.json"
LANE_FILE="$LANE_FILE" BACKEND="$BACKEND" $PY - <<'PY'
import json, os, subprocess
from pathlib import Path
lane = json.loads(Path(os.environ["LANE_FILE"]).read_text(encoding="utf-8"))
assert lane["status"] == "frozen", lane["status"]
row = next((item for item in lane["systems"] if item["provider_key"] == os.environ["BACKEND"]), None)
assert row is not None and row["status"] == "frozen", (os.environ["BACKEND"], row and row["status"])
for path, blob in lane["harness"]["source_blobs"].items():
    if not path.startswith("reference/"):
        continue
    actual = subprocess.run(["git", "hash-object", path], capture_output=True, text=True, check=True).stdout.strip()
    assert actual == blob, (path, actual, blob)
    print(f"{path} blob {actual}: frozen")
(fixture,) = lane["dataset"]["fixtures"]
assert fixture["sha256"] == lane["dataset"]["input_sha256"]
PY
LME_INPUT_SHA256="$(python3 -c "import json;print(json.load(open('$LANE_FILE'))['dataset']['input_sha256'])")"
actual="$(sha256sum "$INPUT" | awk '{print $1}')"
test "$actual" = "$LME_INPUT_SHA256"
echo "input sha256 $actual: frozen"

# Row posture (backend, semantic, recall_control) and the control row's budget, read from the lane
read -r runner_backend semantic recall_control <<< "$(LANE_FILE="$LANE_FILE" BACKEND="$BACKEND" $PY - <<'PY'
import json, os
from pathlib import Path
lane = json.loads(Path(os.environ["LANE_FILE"]).read_text(encoding="utf-8"))
row = next(item for item in lane["systems"] if item["provider_key"] == os.environ["BACKEND"])
configuration = row.get("configuration") or {}
print(configuration.get("backend", row["provider_key"]), configuration.get("semantic_retrieval", "off"), configuration.get("recall_control", "off"))
PY
)"
budget="$(LANE_FILE="$LANE_FILE" $PY - <<'PY'
import json, os
from pathlib import Path
lane = json.loads(Path(os.environ["LANE_FILE"]).read_text(encoding="utf-8"))
control = next(item for item in lane["systems"] if item["role"] == "control")
print(str((control.get("configuration") or {}).get("budget", "none")))
PY
)"
args=(--input "$INPUT" --corpus-class external_frozen --granularity "$PLANE" --output "$OUT/$PLANE-$BACKEND.json" --backend "$runner_backend")
[ "$semantic" != "off" ] && args+=(--agent-memory-semantic-retrieval "$semantic")
[ "$recall_control" != "off" ] && args+=(--agent-memory-recall-control "$recall_control")
# Workflow "Run the lane row": the Mem0 row registers its external backend
[ "$BACKEND" = "mem0_explicit" ] && args+=(--external-backend longmemeval_mem0_explicit_bridge:install_longmemeval_mem0_explicit_backend)
args+=(--agent-memory-budget "$budget")
echo "RUN: python reference/run_longmemeval.py ${args[*]}"
start=$(date -u +%s)
$PY reference/run_longmemeval.py "${args[@]}" 2>&1 | tee "$OUT/run.log"
end=$(date -u +%s)
echo "elapsed_s $((end-start))" | tee -a "$OUT/run.log"

# Execution identity (the workflow's record, with local values where GitHub supplies them)
RUNNER_BACKEND="$runner_backend" LME_INPUT_SHA256="$LME_INPUT_SHA256" LANE_FILE="$LANE_FILE" BACKEND="$BACKEND" PLANE="$PLANE" RUN_ID="$RUN_ID" SHA="$SHA" OUT="$OUT" $PY - <<'PY'
import importlib.metadata as md, importlib.util, json, os, platform, subprocess
from pathlib import Path
def version(name):
    try: return md.version(name)
    except md.PackageNotFoundError: return None
def blob(path):
    return subprocess.run(["git", "hash-object", path], capture_output=True, text=True, check=True).stdout.strip()
lane_file = os.environ["LANE_FILE"]
lane = json.loads(Path(lane_file).read_text(encoding="utf-8"))
validation = json.loads((Path(os.environ["OUT"]) / "lane-validation.json").read_text(encoding="utf-8"))
identity = {
    "evidence_class": "same_harness_external_candidate",
    "agent_memory_revision": os.environ["SHA"],
    "lane_id": lane["lane_id"], "lane_file": lane_file,
    "lane_digest_sha256": validation.get("lane_digest_sha256"),
    "upstream_revision": lane["harness"]["revision"],
    "backend": os.environ["BACKEND"], "runner_backend": os.environ["RUNNER_BACKEND"],
    "granularity": os.environ["PLANE"], "subset_size": "0", "full_selection": True,
    "input_sha256": os.environ["LME_INPUT_SHA256"],
    "runtime_baseline_state": os.environ.get("RUNTIME_BASELINE_STATE"),
    "runtime_baseline_line": os.environ.get("RUNTIME_BASELINE_LINE"),
    "declaration_blob": os.environ.get("DECLARATION_BLOB") or None,
    "source_blobs": {path: blob(path) for path in lane["harness"]["source_blobs"] if path.startswith("reference/")},
    "resolved_packages": {name: version(name) for name in ("agent-memory-reference", "mem0ai", "qdrant-client", "sentence-transformers", "torch", "openai", "posthog", "numpy", "onnxruntime", "tokenizers")},
    "mem0_optional_components": {"fastembed_installed": importlib.util.find_spec("fastembed") is not None, "spacy_installed": importlib.util.find_spec("spacy") is not None},
    "runner": f"local cloud container, {platform.platform()}, Python {platform.python_version()} (not a GitHub-hosted runner)",
    "workflow_run_id": os.environ["RUN_ID"],
    "authority_effect": "none",
}
(Path(os.environ["OUT"]) / "execution-identity.json").write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: identity[k] for k in ("agent_memory_revision", "runtime_baseline_state", "declaration_blob", "lane_digest_sha256", "runner")}, indent=1))
PY
cd "$OUT" && find . -type f -print | sort > files.txt && while IFS= read -r file; do sha256sum "$file"; done < files.txt > sha256.txt
echo "DONE $BACKEND $PLANE -> $OUT"
