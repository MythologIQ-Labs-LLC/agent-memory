# Disclosed pre-review execution of the #809 replay fixture at `871d2bbe`

Not evidence. Recorded so the preregistration history is complete and checkable.

- **What ran:** `python3 -m pytest tests -q -p no:cacheprovider --tb=line --deselect tests/test_809_security_replay_v1.py::Execution`
  from `reference/` (not the repository root) on a clean tree at `871d2bbe`, intended as the full suite with the
  fixture's execution class deselected. The `--deselect` did not take effect (the node id was given relative to
  `reference/`), so `test_809_security_replay_v1.py::Execution` executed the fixture through the DSL/3 runner before
  its independent pre-execution review.
- **Outcome:** `test_every_case_passes` and `test_a_reopened_oracle_would_be_caught` failed; the third test of the
  class (verifier tamper) passed. Failing cases: E1, E1b, E2, E5, E5b, E6, E6a, E6r, E6b. Failing observables, in
  every case: `admitted_*` (`recall_admitted` with `logical_refs` returned every admitted fact of the query, e.g.
  `['bd', 'bn', 'bu', 'bl']` against the expected `['bd']`) and, in E1/E1b/E2, `recall_same_bd` / `recall_same_bl`
  (`False`: unfolded transaction clocks and relevance scores, candidate order). No observable of the deleted-vs-unknown
  kind differed for any other reason.
- **Relation to the review:** the independent review of `871d2bbe` (`independent-replay-review-v1-preexecution.md`)
  found the `recall_same_*` defect independently from the runtime source (RF-1) before seeing any run. It did not find
  the `recall_admitted` probe semantics; the coordinator first described the run's failures as "exactly RF-1" (in the
  `ee427d80` fixture text and in the re-review request), which was wrong, and corrected it from this run's log before
  the runner's first execution. The probe was replaced by the boolean `recall_admits` probe in the next revision.
- **Why it is not evidence:** the run was the test's, not the runner's; it happened before the review; and the runner's
  first execution on a clean tree, committed under `reports/validation/809-security-replays/`, is the only execution
  the family test and the verifier bind to.
- Four unrelated failures of that run (`test_benchmark_author_golden_path`, `test_gauntlet_durability`,
  `test_gauntlet_external_example`, `test_keyed_rebinding_benchmark`) were working-directory artefacts of running from
  `reference/`; all four pass from the repository root.

## Raw summary lines of that run (verbatim from its pytest output)

```text
FAILED tests/test_644_v7_gauntlet_identity.py::ImportedRuntimeIdentity::test_own_checkout_at_frozen_revision_is_served
FAILED tests/test_770_v7_lane_freeze_independent.py::ReplayEvidenceFreshness::test_a_runtime_edit_still_makes_replay_evidence_stale
FAILED tests/test_770_v7_lane_freeze_independent.py::ReplayEvidenceFreshness::test_lane_records_do_not_make_replay_evidence_stale
FAILED tests/test_809_security_replay_v1.py::Execution::test_a_reopened_oracle_would_be_caught
FAILED tests/test_809_security_replay_v1.py::Execution::test_every_case_passes
FAILED tests/test_benchmark_author_golden_path.py::BenchmarkAuthorGoldenPathTests::test_gauntlet_bound_profile_runs_baselines_and_external_contestant
FAILED tests/test_benchmark_integration_contract.py::BenchmarkIntegrationContractTests::test_evaluation_only_change_keeps_runtime_baseline_equivalence
FAILED tests/test_gauntlet_durability.py::DurabilityRecoveryGauntletTests::test_real_agent_memory_public_facade_qualifies_first_durability_slice
FAILED tests/test_gauntlet_external_example.py::ExternalGauntletExampleTests::test_external_example_requires_opt_in_and_completes_probe
FAILED tests/test_keyed_rebinding_benchmark.py::KeyedRebindingBenchmarkTests::test_wave2_harvest_matrix_records_uor_r4_disposition
exit 1
```
