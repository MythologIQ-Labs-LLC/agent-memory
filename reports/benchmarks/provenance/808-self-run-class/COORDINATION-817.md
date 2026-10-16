# Coordination request: 12 mislabelled self-run manifests on `claude/817-jev-mem-execution-no-ci`

**For:** the owner of `claude/817-jev-mem-execution-no-ci`, which Pages discovery allowlists.

**From:** the #808 provenance pass. This session has not pushed to that branch and will not.

## Finding

At `38e80cde`, these 12 manifests under `reports/benchmarks/runs/` declare `task_profile: longmemeval-s-retrieval-parity-v1:<plane>`. That is the id of the **accepted frozen lane**, yet they are self-run executions outside it, run with the v5/v6 scorer blob. The live run-discovery viewer shows them with numeric scores, labelled only "candidate". Each is byte-identical, by git blob, to the audited original on `claude/810-external-exec-no-ci` at `8649219`.

| Manifest (under `reports/benchmarks/runs/`) | Blob |
|---|---|
| `640-hindsight/subset50/session.hindsight_chunks_onnx.manifest.json` | `d38c532b` |
| `640-hindsight/subset50/turn.hindsight_chunks_onnx.manifest.json` | `8b9adfab` |
| `controls/full500/session.agent_memory.manifest.json` | `87ed48b3` |
| `controls/full500/session.lexical_overlap.manifest.json` | `8018080e` |
| `controls/full500/turn.agent_memory.manifest.json` | `208af95f` |
| `controls/full500/turn.lexical_overlap.manifest.json` | `6f9f545e` |
| `controls/subset50/session.agent_memory.manifest.json` | `422ba92a` |
| `controls/subset50/session.lexical_overlap.manifest.json` | `9ee77a1a` |
| `controls/subset50/turn.agent_memory.manifest.json` | `49f42773` |
| `controls/subset50/turn.lexical_overlap.manifest.json` | `653109bc` |
| `mem0/subset50/session.mem0_explicit.manifest.json` | `1f6e099f` |
| `mem0/subset50/turn.mem0_explicit.manifest.json` | `20d0cb9d` |

All 12 are **diagnostic**, not scores:
- the self-run controls (the accepted lane rows remain the baseline);
- a Mem0 reproduction check;
- the Hindsight host-variance subset.

## Requested change

The superseding records are ready. Each is verified to validate on your branch, because all 72 evidence pointers and all 12 superseded-manifest pointers resolve to byte-identical blobs there.

1. **Add the 12 records verbatim.** Copy `reports/benchmarks/self-run-candidates/{640-hindsight/subset50,controls,mem0}/**` from `claude/810-external-exec-no-ci`, plus `reports/benchmarks/self-run-candidates/README.md`:
   ```bash
   git checkout origin/claude/810-external-exec-no-ci -- \
     reports/benchmarks/self-run-candidates/README.md \
     reports/benchmarks/self-run-candidates/640-hindsight/subset50 \
     reports/benchmarks/self-run-candidates/controls \
     reports/benchmarks/self-run-candidates/mem0
   ```
   Each record names the manifest it supersedes, with its SHA-256, and lists every corrected field with its original value.
2. **Choose one of these for the 12 mislabelled originals in `reports/benchmarks/runs/`:**
   - **(a) Recommended:** `git rm` them in a commit whose message names this request. Their bytes stay in history at `38e80cde`, and on `claude/810-external-exec-no-ci` at `8649219`, and each superseding record pins their SHA-256.
   - **(b)** Leave them. Once the fail-closed viewer patch is deployed, they will be refused, and because discovery adopts sources atomically, that would also withhold this branch's Cognee and Jev-Mem progress rows.
3. **Verify offline**, from a checkout of `claude/808-provenance-qualification-no-ci`:
   ```bash
   for f in $(find reports/benchmarks/self-run-candidates -name '*.manifest.json'); do
     python scripts/validate_benchmark_execution_manifest.py "$f" --evidence-root .
   done
   ```
   For this check, the scripts directory comes from that branch; the evidence root is your checkout.
4. **Check live Pages** after the change (#808 direction). The 12 rows should no longer appear under the lane profile.

No raw evidence file changes in any of these steps.
