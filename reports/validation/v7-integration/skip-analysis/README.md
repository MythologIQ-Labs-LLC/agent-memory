# Skipped tests: fresh clone (27) vs working checkout (18)

Both suites ran at `6b3c154d` with CPython 3.12.3 and the pinned requirements, using the repository-root
invocation (`discover -s reference/tests -t reference`, recorded by `skiprun.py`), with `python` resolving to 3.12.

| Checkout | Ran | Failures | Errors | Skipped |
|---|---|---|---|---|
| fresh `git clone` of the pushed branch | 3413 | 0 | 0 | 27 |
| this working checkout | 3413 | 0 | 0 | 18 |

## The difference: 9 tests, one cause

All of them are in `tests.test_seal_anchors`. They skip in a fresh clone because a default `git clone` does not
fetch the `refs/seals/*` namespace that the META_LEDGER session-seal anchors live in. The skip reason states this
and gives the fix, `git fetch origin 'refs/seals/*:refs/seals/*'`. The working checkout has that namespace.

**Confirmed:** after fetching the 23 seal refs into the fresh clone, `tests.test_seal_anchors` runs 12/12 OK with no
skips.

This is an environment property of a default clone, not a code or evidence defect. `scripts/verify_seals.py` fails
loudly, rather than passing, on an empty namespace.

| Test | Reason (exact) |
|---|---|
| `tests.test_seal_anchors.AnchorsMatchTheLedger.test_anchor_commits_are_parentless` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.AnchorsMatchTheLedger.test_anchoring_again_is_a_no_op` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.AnchorsMatchTheLedger.test_every_session_seal_is_anchored_and_matches` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.FailureModesInAScratchClone.test_a_missing_ref_fails` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.FailureModesInAScratchClone.test_a_repointed_ref_fails` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.FailureModesInAScratchClone.test_a_stray_anchor_is_reported` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.FailureModesInAScratchClone.test_anchor_refuses_to_overwrite_a_wrong_ref` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.FailureModesInAScratchClone.test_clean_clone_with_namespace_verifies` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |
| `tests.test_seal_anchors.FailureModesInAScratchClone.test_empty_namespace_fails_rather_than_passing_vacuously` | refs/seals/ not fetched into this checkout: git fetch origin 'refs/seals/*:refs/seals/*' |

## The 18 skips common to both checkouts

| Count | Reason (exact) | Tests |
|---|---|---|
| 7 | graphiti-core and kuzu are not installed | `tests.test_graphiti_substrate.GraphitiSubstrateTests.test_approved_permanent_deletion_removes_physically`<br>`tests.test_graphiti_substrate.GraphitiSubstrateTests.test_high_confidence_cannot_self_authorize_durability`<br>`tests.test_graphiti_substrate.GraphitiSubstrateTests.test_irreversible_deletion_cannot_commit_autonomously`<br>`tests.test_graphiti_substrate.GraphitiSubstrateTests.test_positive_path_persists_and_reconstructs`<br>`tests.test_graphiti_substrate.GraphitiSubstrateTests.test_pruning_tombstones_without_destroying_content`<br>`tests.test_graphiti_substrate.GraphitiSubstrateTests.test_relevance_cannot_cross_tenant_boundary`<br>`tests.test_graphiti_substrate.GraphitiSubstrateTests.test_supersession_marks_without_deleting` |
| 4 | pinned representation unavailable: optional extra 'semantic' not installed (onnxruntime) | `tests.test_representation_onnx.ProviderTests.test_golden_vectors_and_topk_order`<br>`tests.test_representation_onnx.ProviderTests.test_spec_and_unit_norm_float32`<br>`tests.test_representation_onnx.ProviderTests.test_tampered_model_file_is_refused`<br>`tests.test_representation_onnx.ProviderTests.test_truncation_at_512_tokens` |
| 3 | optional dependency not installed: numpy | `tests.test_package_layout.LayoutMatchesMover.test_every_alias_is_the_identical_object (module='long_horizon_benchmark')`<br>`tests.test_package_layout.LayoutMatchesMover.test_every_alias_is_the_identical_object (module='long_horizon_dataset')`<br>`tests.test_package_layout.LayoutMatchesMover.test_every_alias_is_the_identical_object (module='operational_memory_benchmark')` |
| 2 | upstream-compatible record sampling requires numpy | `tests.test_agentmembench.RetrievalPhaseTests.test_exact_source_recall_and_upstream_sampling`<br>`tests.test_agentmembench.RetrievalPhaseTests.test_load_records_is_seeded_stratified_and_source_unique` |
| 1 | file permissions are not enforced for root | `tests.test_802_semantic_cache_deletion.SemanticSidecarLifecycleTests.test_read_only_sidecar_reports_incomplete_cleanup_without_blocking_recovery` |
| 1 | pinned representation model not provisioned | `tests.test_facade_recall_control.FacadeShadowRecallControlTests.test_semantic_cap_binding_with_the_pinned_model` |

None of these involves a test that was skipped to hide a failure. The common skips are of five kinds:

- optional extras that are not installed (graphiti-core/kuzu, onnxruntime, numpy);
- one representation model that is not provisioned;
- one POSIX-permission check that cannot hold when the suite runs as root.

They are the same in both checkouts. `expected failures`: 1 in each (`tests.test_786_cross_scope_write_authority.EvidenceReferenceOracle.test_fr3_2_citing_a_deleted_foreign_uuid_is_observable_to_the_citer`).
