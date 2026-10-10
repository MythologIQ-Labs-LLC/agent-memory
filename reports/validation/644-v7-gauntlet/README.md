# #644 v7 public Gauntlet contestant: validation evidence

This is the independent validation of `implementation/644-v7-gauntlet-contestant-no-ci` @ `e3847942`, and of its repair on `validation/644-v7-gauntlet-contestant-independent`.

The verdict and the full report are in [`QUALIFICATION.md`](QUALIFICATION.md).

**This is not v7 acceptance, qualification or publication.**

## Layout

| Path | Content |
|---|---|
| `runs/asis/` | The Gauntlet probe at `e3847942`, with the correct runtime on `PYTHONPATH`. |
| `runs/wrong/` | The same run at `e3847942` using a foreign editable install (D2). It completes and is mislabelled. |
| `runs/after_correct/`, `runs/after_wrong/` | The same two runs at `b854d5e`. The first completes; the second is blocked by `runtime_identity_unverified`. |
| `identity/*/identity-<pid>.json` | The git blob of every `agentmem_ref` module each process loaded, captured by `scripts/identity_capture_sitecustomize.py`. |
| `identity/tree_16a248b.txt` | `git ls-tree -r 16a248b reference/agentmem_ref`, the comparison tree. |
| `logs/` | The complete stdout and stderr of every command in QUALIFICATION.md sections 2 and 3. |
| `lane-gate-probe.json` | The workflow and importer preconditions applied to the declared v7 lanes (D3), from `scripts/lane_gate_probe.py`. |
| `amb-compare.txt` | The local AMB PrecisionMemBench agent-memory row at `b854d5e` compared with the accepted v6 evidence. |
| `replay-verify-b854d5e.json`, `inventory-b854d5e.json` | The replay verifier (`--reexecute`) and the inventory checker at `b854d5e`. |
| `scripts/lme_compare.py` | The LongMemEval-S comparison with the accepted v6 evidence: headline, metrics, governance, and a per-question digest. |

## Reproduce

Run everything from the repository root at `b854d5e`, with a venv in which `agent-memory` is installed.

```
export PYTHONPATH=$PWD/reference                    # required unless this checkout is the editable install
python -m unittest discover -s reference/tests -t reference -p 'test_644_v7_gauntlet_*.py'
agent-memory gauntlet validate-adapter examples/gauntlet/agent-memory-runtime-baseline-v7.json
agent-memory gauntlet run --system examples/gauntlet/agent-memory-runtime-baseline-v7.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 --allow-external-process --allow-destructive-reset --output-dir <dir>
python -m unittest discover -s reference/tests -t reference
python scripts/check_runtime_baseline_equivalence.py --candidate HEAD
```

### Optional steps

**Capture the imported runtime.** Prepend `reports/validation/644-v7-gauntlet/scripts` to `PYTHONPATH`, after copying `identity_capture_sitecustomize.py` there as `sitecustomize.py`, and set `V7G_IDENTITY_DIR=<dir>`.

**Reproduce D2.** Before the repair, point `PYTHONPATH` at another checkout's `reference/`, one whose runtime differs. Before the repair, the run completes; after it, the run is refused.

**Local AMB and LongMemEval-S rows.** These need the frozen datasets, which are not in this repository. QUALIFICATION.md section 5 names the inputs and digests.
