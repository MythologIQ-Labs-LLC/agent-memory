# Integration candidate evidence at `1d0d4c75` (claude/eager-dirac-bftkfg-stack-main)

Candidate evidence for the integrated runtime stack #783 → #784 → #788 → #804 reconciled with
`main` `38f6a7dc`, **not** acceptance and not a baseline publication. Produced locally (no GitHub
Actions, no hosted CI, no paid provider; the semantic-route tests use the offline deterministic
representation provider).

- runtime source commit: `1d0d4c7590176474006e6c037fac38ebcfe10d09`
  = PR #804 head `74cb4a09e2da5614f27890ea02399d771920fe32` (on #788 `5a33bdde` → #784 `060e7cd7` → #783 `c785af90`)
  merged with `main` `38f6a7dcc358e8ee50a38d703b0addb9d8e660d7` (#797 documentation; `docs/README.md` auto-merged)
  plus the catalog filing of docs 76-82 (`docs/ARCHITECTURE_INDEX.md`, register entries only).
- protected blobs (`pyproject.toml`, `reference/agentmem_ref`) and every file under `reports/`, `schemas/`,
  `examples/` are identical between `74cb4a09` and `1d0d4c75` (`git ls-tree` comparison).
- the evidence commit that adds this directory sits on top of `1d0d4c75`; it changes no protected blob.

| evidence | command (repository root, clean tree) | outcome |
|---|---|---|
| three #786 security replay contracts (`786-security-replay-dsl/1`, `-v2`) | `python3 reference/run_786_security_replays.py --all --output-dir <scratch>`, then `python3 scripts/verify_786_security_replays.py --evidence-root <scratch> --reexecute` (exit 0) | all three `VERIFIED` / `PASS` / re-executed, 28/28 cases (`security-replays/`, `security-replays/security-verify-reexecute.json`); the committed copy verifies again without re-execution (exit 0). The `9c4e9178` evidence under `reports/validation/786-security-replays/` is untouched |
| five #644 v7 replay contracts | `python3 reference/run_644_v7_replays.py --all --output-dir <scratch>`, then `python3 scripts/verify_644_v7_replays.py --reexecute --evidence-root <scratch>` (exit 0) and `python3 scripts/check_644_v7_replay_inventory.py --evidence-root <scratch>` (exit 2, BLOCKED by design: acceptance needs an independent reviewer's ledger decision) | all five `VERIFIED` / `PASS` / re-executed, 104/104 cases (`replays/verify-reexecute.json`) |
| public Gauntlet probe through the public facade | scratch contestant (the v7 stdio adapter with `FROZEN_RUNTIME_REVISION=1d0d4c75…`, `PUBLIC_CONTRACT_VERSION=1.7.0`; not committed) run with `PYTHONPATH=reference python3 -m agentmem_ref.console gauntlet run --system examples/gauntlet/agent-memory-runtime-candidate.json --profile gauntlet-orchestration-retrieval-probe-v1 --output-dir <scratch> --allow-external-process --allow-destructive-reset --json` | `status: complete`, `exact_top1 1.0`, `correct_top1 3/3`, `authority_effect none` (`gauntlet/`) |
| blind theatre and vineyard holdouts (served-memory quality evaluator v3 @ `9961067`) | scratch harness identical to `reports/validation/774-on-integrated-head/measure_head.py`, run on `060e7cd7` and `1d0d4c75` in `composed` and `strict-target` modes | rate-identical on both heads: theatre top1_critical 0.4286 composed / 0.7619 strict-target, vineyard 0.45 / 0.90; P0 prohibited and stale exposures 0 on every run; both runtimes clean at their commits (`blind-holdouts/summary.json`) |
| focused #802 cache, permanent deletion, recovery and developer facade | `python3 -m pytest reference/tests/test_representation_cache.py reference/tests/test_802_semantic_cache_deletion.py reference/tests/test_semantic_route_policy_320.py reference/tests/test_developer_facade.py -q` | 66 passed, 1 skipped (root cannot test file permissions), 11 subtests |
| #774/#776/#777 lineage and disclosure, #786 cross-scope write authority and security replays, deletion authority and completeness | `python3 -m pytest reference/tests/test_deletion*.py reference/tests/test_77[4-7]*.py reference/tests/test_786*.py -q` (22 modules) | 201 passed, 133 subtests |
| restart, recovery, scope, isolation, tenancy, shared revocation, checkpoint | `python3 -m pytest reference/tests/test_{restart,recover,scope,isolation,tenant,shared_revocation,checkpoint}*.py -q` | 62 passed |
| durability gauntlet through the real facade (DUR-DEL-001 included) | `python3 -m pytest reference/tests/test_gauntlet_durability.py reference/tests/test_benchmark_author_golden_path.py reference/tests/test_gauntlet_external_example.py -q` from the repository root | 14 passed (from `reference/` these and `test_keyed_rebinding_benchmark` fail on repository-relative paths: a cwd artefact, not a runtime finding) |
| root-level tests (architecture catalog validator, #797) | `python3 -m unittest discover -s tests -p 'test_*.py'`; `python3 scripts/validate_architecture_index.py` | 19 tests OK; catalog valid, 82 numbered docs, exactly one shelf each |
| full reference suite | `python3 -m pytest reference/tests -q` from the repository root | 2917 passed, 4 failed, 35 skipped, 1865 subtests passed (4m16s). The four failures are exactly the freeze guards red by design on any undeclared protected change (`test_644_v7_gauntlet_identity…test_own_checkout_at_frozen_revision_is_served`, the two `test_770_v7_lane_freeze_independent.ReplayEvidenceFreshness` cases, `test_benchmark_integration_contract…equivalence`); they fail identically on the unmodified parent `f7ceb5aa` and on `5a33bdde`, and the guard modules do not exist on `main` |
| reference conformance report | `python3 reference/run_conformance.py` | fixtures_failed `[]` (every fixture passed), 3218 trials, `deletion_residue_rate 0.0`, 2945 governance paths executed; `known_failures` lists exactly the four by-design freeze guards; `conformance_level 0` as before (no level is claimed) |
| Runtime Baseline equivalence and declaration | `python3 scripts/check_runtime_baseline_equivalence.py` (real register) → exit 1 by design: six undeclared protected changes, two v7 blob mismatches, undeclared identity 1.6.0 → 1.7.0; `… --register reports/runtime/proposals/786-scratch-register-v8.DEMO.json --candidate HEAD` → `TRANSITION` (14 declared blobs, exit 0); `… --pinned-only` → exit 1 by design; the declaration validates against `schemas/runtime-baseline-declaration.schema.json` | the cumulative v6 → v8 declaration pins exactly this candidate's protected tree; nothing is activated |
| retain timing | `perf-retain-ab.txt` | 5.9 ms/write on the candidate against 6.0 on `060e7cd7` (1000 writes), within run-to-run noise |

## Security findings closed in this candidate relative to PR #804's reviewed head `f7ceb5aa`

| id | finding | evidence |
|---|---|---|
| R3 | the active semantic route constructed the derived store through a symlinked `derived` directory before the recovery reconciler could refuse it (reviewer) | regression fails on `f7ceb5aa`, passes at `74cb4a09`; `auto` degrades, `required` refuses before I/O |
| R4 | the post-open re-check was bypassed by swapping the parent directory in and back out around SQLite's open (this session); `os.chmod` by path followed a swapped-in leaf link | parent-swap and leaf-swap regressions fail on `f7ceb5aa`/`059670c1`, pass at `74cb4a09`; opens are descriptor-pinned and verified through the process descriptor table |
| R5 | discard of any unreadable or mis-identified file under our name was destructive to another version's data (owner challenge) | foreign stores are kept, reported and make deletion loud; regressions at `74cb4a09` |

## What this is not

Not acceptance, not a Runtime Baseline publication, not an erasure claim about rollback journals,
backups, snapshots or the filesystem, and not a claim that a concurrent directory swap by a principal
with write access to the root is defeated (that principal is inside the trust boundary the canonical
SQLite file already requires). Statuses: IMPLEMENTED, TESTED (locally), INDEPENDENTLY REVIEWED (#788:
three reviews; #804: three reviews, the third answered with two further findings of this session);
NOT DECLARED (proposal only), NOT QUALIFIED, NOT MERGED.
