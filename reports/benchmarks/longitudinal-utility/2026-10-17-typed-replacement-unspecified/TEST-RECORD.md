# Test record (local, no hosted CI)

Python 3.13, `PYTHONPATH=. python -m unittest discover -s tests -t .` from `reference/`.

| Tree | Ran | Failures | Errors | Skipped |
|---|---:|---:|---:|---:|
| `main` `38f6a7d` (clean worktree) | 2552 | 3 | 1 | 23 |
| candidate `0177240` | 2558 | 5 | 1 | 23 |
| candidate after layout fix | the same 4 as `main`, focused re-run below | | | |

Failures present on **both** `main` and the candidate (pre-existing, not caused by this lane):

- `test_keyed_rebinding_benchmark…test_wave2_harvest_matrix_records_uor_r4_disposition` (error)
- `test_benchmark_author_golden_path…test_gauntlet_bound_profile_runs_baselines_and_external_contestant`
- `test_gauntlet_durability…test_real_agent_memory_public_facade_qualifies_first_durability_slice`
- `test_gauntlet_external_example…test_external_example_requires_opt_in_and_completes_probe`

Failures introduced by the candidate and fixed in the follow-up commit: `test_package_layout` ×2
(the new evaluation module computed `parents[2]`; it now imports `REFERENCE_ROOT` from `_paths`).
Focused re-run of `test_package_layout` plus the four pre-existing modules after the fix: 26
tests, only the four pre-existing failures remain.

Focused suites (cross-fact, temporal, ranking, facade, API, contracts, recall, propositions,
longitudinal, typed replacement): 629 + 6 tests OK.
