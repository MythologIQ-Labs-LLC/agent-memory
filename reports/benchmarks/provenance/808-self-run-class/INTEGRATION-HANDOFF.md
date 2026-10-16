# Integration handoff: self-run candidate class (#808 G1)

This is narrow and authorizes nothing: there is no merge, no PR, no deployment and no admission.

## Change sets and where they land

| # | What | Branch @ commit | Lands where | Who decides |
|---|---|---|---|---|
| 1 | Schema block `candidate_class`, validator rules, builder, 59 tests, catalog-contract docs | `claude/808-provenance-qualification-no-ci` @ `0b4df6bb` (on top of the #807/#808 qualification `5a86518e`, `c593a6f8`) | Together with the `implementation/807-benchmark-execution-envelope-no-ci` change, as one isolated PR once an Actions budget is approved | #808 owner (D1) |
| 2 | 21 superseding self-run records | `claude/810-external-exec-no-ci` @ `f57d5a66` | They stay on the evidence branch. **Not** `main`, **not** `reports/benchmarks/normalized/` | #808 owner (D1) |
| 3 | Relabelling of 12 records on the Pages-allowlisted branch | Prepared; request on #817 | `claude/817-jev-mem-execution-no-ci` | That branch's owner (D2) |
| 4 | `run-discovery.js` fail-closed patch | `pages-discovery/run-discovery-fail-closed.patch` (base `gh-pages` `4cf72d1f`) | `gh-pages`, after item 3 | Pages owner, #807 (D3) |

**Files in change set 1:**
- `schemas/benchmark-execution-manifest.schema.json`;
- `scripts/validate_benchmark_execution_manifest.py`;
- `scripts/build_self_run_candidate_records.py`;
- `tests/test_benchmark_execution_manifest.py`;
- `docs/benchmark-evidence-console-catalog.md`.

The provenance reports under `reports/benchmarks/provenance/` are evidence, not code.

## Verification to repeat before merging change set 1 (offline)

```bash
python -m unittest discover -s tests -p 'test_benchmark_execution_manifest.py' -v   # 59/59
python -m unittest discover -s tests                                             # all OK
python scripts/validate_schemas.py                                               # 75 schemas
python scripts/build_benchmark_scorecards.py --check && python scripts/build_benchmark_ui_catalog.py --check
python scripts/build_self_run_candidate_records.py --evidence-root <checkout of claude/810-external-exec-no-ci> --check
```

## Migration risk

- **No existing manifest changes shape.** `schema_version` stays `1.0.0`.
- **The new lane-claim rule refuses manifests that name a frozen lane without that lane's evidence.** Today that is exactly the 16 mislabelled self-run originals, which are superseded. No accepted lane row is enveloped yet, so none is affected.
- **Scorecards, the catalog and the snapshot are unaffected.** `--check` is current.

## Still not done, by design

- **Admission: 0/21.** That needs G2: an independent reviewer and an owner-published review-authority digest.
- **No numeric score is shown publicly for a self-run record.**
