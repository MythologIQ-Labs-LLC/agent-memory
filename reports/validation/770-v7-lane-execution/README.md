# #770 v7 lane execution evidence

The report is [`QUALIFICATION.md`](QUALIFICATION.md). **This is not v7 acceptance.**

| Path | Content |
|---|---|
| `runs.json` | All nine lane runs and both imports: run IDs, workflow, complete inputs, head SHA, conclusion, timestamps, artifact ID, size and zip sha256. |
| `results/verify-imported.json` | Every imported record re-verified from the committed bytes with the importers' own refusal functions. |
| `results/compare-v6-v7.json` | Question-by-question and case-by-case comparison with the accepted v6 evidence, plus aggregates, governance and efficiency. |
| `results/{amb,lme}-attribution.{json,log}` | `scripts/check_cross_fact_attribution.py`, run with the v6 root as `--v4-dir` and the v7 root as `--v5-dir`. |
| `results/currentness.txt` | `latest_gold_first`, the knowledge-update slice and the cross-fact summaries. |
| `results/v6-byte-identity.txt` | The v6 evidence and lane tree hashes on `main` and on this branch. |
| `diagnosis/` | The Mem0 turn-plane reorder analysis and the tokenizers check. |

## Reproduce

Run from this branch's root (no network, no Actions):

```
PYTHONPATH=reference python reports/validation/770-v7-lane-execution/scripts/verify_imported_v7.py .
python reports/validation/770-v7-lane-execution/scripts/compare_v6_v7.py .
python scripts/check_cross_fact_attribution.py --benchmark longmemeval \
  --v4-dir reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6 \
  --v5-dir reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v7
python scripts/check_cross_fact_attribution.py --benchmark amb \
  --v4-dir reports/benchmarks/amb/amb-precisionmembench-retrieval-v6 \
  --v5-dir reports/benchmarks/amb/amb-precisionmembench-retrieval-v7
```
