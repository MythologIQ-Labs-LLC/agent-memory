# #786 candidate evidence at `8d7ed43f` (claude/eager-dirac-bftkfg-786-write-authority)

Candidate evidence for the cumulative runtime candidate (#776/#777/#772/#774/#786), **not**
acceptance and not a baseline publication. Produced locally (no GitHub Actions, no hosted CI,
no paid provider).

- source commit: `8d7ed43f3e7e042310781788d2eff72a6cf65763` (the review-remediated head; the same evidence was first produced at the pre-remediation head `36a6ef4d`, whose independent review is recorded in `docs/786-cross-scope-write-authority.md`)
- stacked on PR #784 head `060e7cd7` (which stacks on PR #783 head `c785af90`, on `main` `3eebb6d5`)

| evidence | command (repository root) | outcome |
|---|---|---|
| public Gauntlet probe through the public facade | `PYTHONPATH=reference python3 -m agentmem_ref.console gauntlet run --system examples/gauntlet/agent-memory-runtime-candidate.json --profile gauntlet-orchestration-retrieval-probe-v1 --output-dir <scratch> --allow-external-process --allow-destructive-reset --json` (scratch contestant: the v7 stdio adapter with `FROZEN_RUNTIME_REVISION=8d7ed43f…`, `PUBLIC_CONTRACT_VERSION=1.7.0`; not committed) | `status: complete`, `exact_top1 1.0`, `correct_top1 3/3`, `authority_effect none` (`gauntlet/`) |
| five #644 v7 replay contracts | `python3 reference/run_644_v7_replays.py --all --output-dir <scratch>` on a clean tree, then `python3 scripts/verify_644_v7_replays.py --reexecute --evidence-root <scratch>` (exit 0) and `python3 scripts/check_644_v7_replay_inventory.py --evidence-root <scratch>` (exit 2, BLOCKED by design: acceptance needs an independent reviewer's ledger decision) | all five `VERIFIED` / `PASS` / re-executed (`replays/verify-reexecute.json`) |
| blind theatre and vineyard holdouts (served-memory quality evaluator v3 @ `9961067`) | scratch harness identical to `reports/validation/774-on-integrated-head/measure_head.py`, run on `060e7cd7` and `8d7ed43f` in `composed` and `strict-target` modes | byte-identical quality on both heads: theatre top1_critical 0.4286 composed / 0.7619 strict-target, vineyard 0.45 / 0.90; P0 prohibited and stale exposures 0 on every run (`blind-holdouts/summary.json`) |
| durability gauntlet through the real facade (DUR-DEL-001 included) | `python3 -m pytest reference/tests/test_gauntlet_durability.py reference/tests/test_benchmark_author_golden_path.py reference/tests/test_gauntlet_external_example.py -q` from the repository root | passed (these spawn stdio adapters with repository-relative paths; run from `reference/` they fail with `adapter_exited`, which is a cwd artefact, not a runtime finding) |
| focused #786 suite | `python3 -m pytest reference/tests/test_786_cross_scope_write_authority.py -q` | 31 passed (the 23 preregistered cases, 18 of which fail on `060e7cd7`, plus the 8 ported review findings) |
| full reference suite | `python3 -m pytest reference/tests -q` from the repository root | see the PR description for the exact count; the four freeze guards that are red by design on any undeclared protected change (`test_644_v7_gauntlet_identity`, two `test_770_v7_lane_freeze_independent::ReplayEvidenceFreshness`, `test_benchmark_integration_contract…equivalence`) stay red until a successor is declared |

The runtime-quality numbers above are reported separately from the P0 safety exposures, as the
evaluator requires; none of them is a composite score and none is benchmark acceptance.

| retain timing | `perf-retain-ab.txt` | 1000 fresh `remember` calls, three A/B alternations under one filesystem: 5.7–6.3 ms/write on `060e7cd7`, 6.1–6.5 ms/write on `8d7ed43f`; cumulative 6.0–6.4 s on both; within the run-to-run spread |
