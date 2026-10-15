# Independent repeat: Agent Memory and lexical controls, full 500 LongMemEval-S (2026-10-15)

This run repeats `../full500/` in a different container. The code, evaluator, input sha256
`d6f21ea9…a3442` and environment are the same: `am-venv-freeze.txt` is byte-identical to the
original. Command and exit status are in `controls-500.exec.json` (exit 0, 2768 s on a shared
4-vCPU host, run as an unprivileged user with no credentials).

**Result: every row is identical.** The comparison covers 500 questions × 2 planes × 2 backends,
2,000 rows in all, across metrics, status, runtime_error, ranked_top, gold and question_type
(`scripts/compare_longmemeval_rows.py --scope exact`); timing fields are excluded. Headlines are
equal too:

| Backend | session recall_all@5 | session recall_all@10 | turn recall_all@10 | turn recall_all@50 |
|---|---:|---:|---:|---:|
| agent_memory | 0.823389 | 0.892601 | 0.72315 | 0.859189 |
| lexical_overlap | 0.73031 | 0.825776 | 0.587112 | 0.761337 |

The control is therefore deterministic across hosts. Run-to-run differences in a competitor are
the competitor's own, not the harness's.
