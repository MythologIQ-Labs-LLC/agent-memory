# Public Gauntlet orchestration probe: v7 contestant re-pinned to the repaired candidate `2ad4cf23`

Independent Gauntlet qualification engineer, 2026-10-21, isolated full-history worktree at branch head
`97368d6746de6402c99e4b6f1aa3c39e742ee9fa` (`review/836-v7-gauntlet-repin-no-ci`), clean tree, no editable
install of `agentmem_ref` anywhere on the machine (`pip show agent-memory`: not installed; `import agentmem_ref`
outside the checkout: `ModuleNotFoundError`). The adapter imported `/home/user/wt-gauntlet/reference/agentmem_ref`
through `PYTHONPATH=reference` only. No protected runtime, lane, declaration, fixture, gold or v6 byte changed.
No GitHub Actions. No other benchmark process was running on this machine (checked by process list).

| Identity | Value |
|---|---|
| Repaired runtime revision | `2ad4cf23d366fc784a486b0245550230e64bfa25` (ancestor of this head; `git diff --name-only 2ad4cf23 HEAD -- reference/agentmem_ref reports/runtime/baseline-v7-declaration.json` empty) |
| Protected tree `reference/agentmem_ref` | `f9b5ff9e79a54ef053ce89eb975256b63e211714` at `2ad4cf23` and at this head |
| Declaration blob | `7de94f11d7d521f07d2fe22317662ac6f92f89fa`; `recall_control.py` `9fa861c36d9edde2df746c8e089a658576ea3bf4` |
| Adapter blob | `0f2f18b0d1ec62edc2a1d424af6cbaa967774ec2` = manifest `adapter.revision` (recomputed with `git hash-object`) |
| Manifest blob | `a41e3e1f752ce8bd0d0bda4ce2b5bbf057b236da`; `system.revision` `git-commit:2ad4cf23…`; schema `gauntlet-system-adapter.schema.json` VALID |
| Configuration digest | `sha256:e4548a487b8c83ef9172bb9076933b493a7d91b9de2239fd5409f7992b88ff82`, recomputed from the recorded v5/v6 basis (`identity-recomputation.txt`) |
| Public contract declared | `1.8.0` (provisional; `api/contract.py` `CONTRACT_VERSION = "1.8.0"`; not a contract-acceptance decision) |
| Environment | Python 3.13.16 (`/usr/bin/python3.13`; `python` resolves to the same), Linux 6.18.44 x86_64, `reference/requirements.txt` pins |

## Steps and results

1. **Tests** (`test-modules.txt`): `tests.test_644_v7_gauntlet_contestant` 2/2, `tests.test_644_v7_gauntlet_identity` 4/4 (`cd reference && python3 -m unittest -v …`).
2. **CLI validation** (`validate-adapter.txt`): `PYTHONPATH=reference python3 -m agentmem_ref.console gauntlet validate-adapter examples/gauntlet/agent-memory-runtime-baseline-v7.json` (the `agent-memory` console entry point, `agentmem_ref.console:main`, invoked as a module because the package is deliberately not installed): `Gauntlet adapter: valid`, manifest digest `135706f2…`.
3. **Probe** (`run-result.json`, `native-results.json`, `normalized-run.json`, `qualification.json`, `adapter-manifest.json`, `execution-identity.txt`), from the repository root after clearing the disposable state root `/tmp/agent-memory-gauntlet-runtime-baseline-v7`:

   ```
   PYTHONPATH=reference python3 -m agentmem_ref.console gauntlet run \
     --system examples/gauntlet/agent-memory-runtime-baseline-v7.json \
     --profile gauntlet-orchestration-retrieval-probe-v1 \
     --output-dir <scratch> --allow-external-process --allow-destructive-reset --json
   ```

   Result: exit 0, `status: complete`, `sample_count 3`, `correct_top1 3`, **`exact_top1 1.0`** (cobalt, amber, cedar each exact at top-1), `authority_effect none`, transcript `frozen_runtime_revision 2ad4cf23…`, `public_contract 1.8.0`, run elapsed 607 ms, operation p50 32 ms. The committed artifacts keep the absolute scratch paths the orchestrator wrote.
4. **Runtime identity actually imported** (`describe-runtime-identity.json`, same clean state, same `PYTHONPATH`): `verified: true`, `same_checkout: true`, `matches_frozen_revision: true`, `imported_package /home/user/wt-gauntlet/reference/agentmem_ref`, `frozen_runtime_tree f9b5ff9e…`. The orchestrator's artifacts record each operation's `result` but not the adapter's `adapter_evidence.runtime_identity`; a `complete` run nevertheless implies the guard passed, because an unverified identity turns every operation into `system_error` (step 5). Recording `adapter_evidence` in the transcript would make the artifacts self-sufficient; noted, not changed here.
5. **Fail-closed guard, independent matrix** (`fail-closed-matrix.txt`, worktree restored to clean after each arm):
   - A control, clean tree: served, verified.
   - B protected runtime changed (one comment appended to `runtime/adapter.py`): `runtime_identity_unverified`; full probe `status: blocked`, exit 1, no `exact_top1` (`fail-closed-B-changed-runtime-probe.json`).
   - C untracked file inside the runtime boundary: refused. D control, untracked file under `evaluation/` (outside the Runtime Baseline source boundary): served.
   - E byte-identical copy of `agentmem_ref` in a foreign directory on `PYTHONPATH`: refused with `same_checkout: false` even though `matches_frozen_revision: true`; with the orchestrator itself importing that copy the CLI stops earlier with `Gauntlet schema unavailable` (`status: invalid`, exit 2; `fail-closed-E-foreign-orchestrator-import.json`), an infrastructure failure of the orchestrator import, not the adapter guard. F foreign copy shadowing the checkout on `PYTHONPATH`: refused.
   - E2 full probe with the orchestrator from the checkout and only the adapter child importing the foreign copy (scratch manifest, startup wrapped in `env PYTHONPATH=…`, not committed): `status: blocked`, `runtime_identity_unverified` (`fail-closed-E2-foreign-import-probe.json`). No evidence under a false source identity was produced in any arm.
   - G this adapter run from a checkout at the pre-repair runtime `07cd8692`: refused, `matches_frozen_revision: false`.
6. **Failure attribution.** All refusals carried `source: system_adapter`, `code: runtime_identity_unverified`; no `system_under_test` error appeared in any run. No adapter, infrastructure or runtime failure occurred in the qualifying run.

## What this is and is not

A passing three-query public Gauntlet probe for the v7 contestant at the repaired candidate: the publication
acceptance gate's shape for that probe (docs/67), not a score and not authority. It is **not** Runtime Baseline v7
acceptance: the register still ends at v6, no `baseline-v7-qualification.json` or v7 register entry exists,
equivalence is `TRANSITION`, security sign-off, acceptance of public contract `1.8.0` and consumer installation
qualification are separate decisions, and the LongMemEval `mem0_explicit` comparator rows were still pending at
execution time. The published v6 record, lanes and gold are untouched.
