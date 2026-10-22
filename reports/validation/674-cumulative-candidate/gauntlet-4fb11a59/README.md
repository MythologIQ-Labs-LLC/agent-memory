# Candidate-only public Gauntlet probe on the folded head `4fb11a5982f227f02a2c538f83700518061aa651`

The owner's candidate-only re-pin (`review/836-v7-gauntlet-repin-no-ci` @ `97368d67`, four commits taken
unchanged by merge commit `4fb11a59`) binds the v7 stdio adapter to contract `1.8.0` and source revision
`2ad4cf23` (protected runtime tree `f9b5ff9e…`, identical at every commit of this branch since the repair).
Everything below ran from this checkout at `4fb11a59` with `PYTHONPATH=reference`, CPython 3.12.3,
after the lane evidence had settled (`a0f0680c`). **Unqualified transition probe**: no B1/B2 publication,
no security acceptance, no accepted v6 evidence or register bytes touched.

| Step | Command | Result |
|---|---|---|
| contestant + identity tests | `python -m unittest -v tests.test_644_v7_gauntlet_contestant tests.test_644_v7_gauntlet_identity` (from `reference/`) | 6/6 OK (`tests.txt`) |
| adapter validation | `python -m agentmem_ref.console gauntlet validate-adapter examples/gauntlet/agent-memory-runtime-baseline-v7.json` | valid: system `git-commit:2ad4cf23…`, adapter `git-blob:0f2f18b0…`, authority effect none (`validate-adapter.txt`); manifest configuration digest `sha256:e4548a48…` |
| external-process probe | `python -m agentmem_ref.console gauntlet run --system examples/gauntlet/agent-memory-runtime-baseline-v7.json --profile gauntlet-orchestration-retrieval-probe-v1 --allow-external-process --allow-destructive-reset --output-dir <disposable>` | `status: complete`, `sample_count 3`, `correct_top1 3`, **`exact_top1 1.0`**; normalized run binds `git-commit:2ad4cf23…` / `git-blob:0f2f18b0…` (`probe/`: `qualification.json`, `native-results.json`, `normalized-run.json`, `adapter-manifest.json`; `probe.txt`) |
| negative source-mismatch control | same command with `PYTHONPATH` pointed at an `origin/main` (`7d4c9be6`) worktree's `reference/` | `Execution: blocked`, `system_adapter / runtime_identity_unverified: imported agentmem_ref is not this checkout's runtime at FROZEN_RUNTIME_REVISION` (`control/`, `control.txt`): the fail-closed guard is intact |
| runtime baseline checker at this head | `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` | TRANSITION, unchanged |

The same four steps were run earlier from a detached worktree of `97368d67` before the fold-in, with the
same outcomes (`../gauntlet-repin-precheck-97368d67/`).
