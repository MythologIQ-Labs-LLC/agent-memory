# AMB v6 source replay and diagnostic completeness

This correction is stacked on draft PR #793. It is **not new benchmark evidence**, does not change native passes, and does not update the canonical dashboard.

The original dossier extracted diagnostic flags from the native report's abbreviated `judge_reason` string. The native report has a complete `meta.failures` array that can contain additional failures. Source replay independently found two BM25 cases where the abbreviated string omitted a native *missing expected belief*:

- `relation-participant-open-question-routes-correctly`
- `negation-query-still-surfaces-rejected-tool`

The flags in the case dossier now use `meta.failures` and capture both cases. **Agent Memory 15/77, Mem0 10/77, BM25 8/77, all means, the 6/1 paired discordance, and the McNemar p-value are unchanged.** The original native files and gold labels remain untouched.

Reproduce without CI or inference, from an actual repository checkout:

```bash
python scripts/check_789_case_dossier.py
python -m unittest discover -s reference/tests -p test_789_case_dossier_replay.py -v
python -m unittest discover -s reference/tests -p test_789_qualitative_review_contract.py -v
```

The replay requires the exact Git blob SHA of each native source file, 77 unique shared case IDs, matching query and gold arrays, native case verdict/observations, complete diagnostic flags, summary totals, native summary metrics, paired matrix, category breakdown, exact McNemar calculation, frozen 24-case selection and non-promotion status. It fails closed on mismatches.

**Limits:** These are historical retrieval-only native scorer outcomes. Human review is still zero forms, true reviewer identity/blinding and citation linkage are not established by the current structural checker, and nothing authorizes a product superiority or runtime-success claim. Exact-tree replay on this GitHub branch has not been executed by a runtime with a full checkout; the new script's twelve synthetic unit controls were executed in an isolated local reconstruction.