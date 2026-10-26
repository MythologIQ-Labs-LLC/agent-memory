# #644 v7 public Gauntlet contestant: independent validation

## Verdict

**`e3847942`: CHANGES REQUIRED.** It has two defects:
- **D1:** its configuration-digest basis diverges from the v5/v6 records.
- **D2:** its evidence can be labelled with a runtime revision it did not run.

Both are repaired on this validation branch, at **`b854d5e`**, with failing reproducers committed first (`29d4b79`). No protected runtime change was needed.

**Formal v7 qualification remains BLOCKED.** Specifically:
- workflow-imported v7 Gauntlet evidence cannot exist before Runtime Baseline B1 publication, by design;
- the declared AMB and LongMemEval lanes cannot produce v7 evidence as declared (D3);
- the replay evidence still awaits independent acceptance.

A passing local probe is not acceptance.

## 1. Identity checks (step 1)

| Check | Result |
|---|---|
| Branch | `implementation/644-v7-gauntlet-contestant-no-ci` @ **`e3847942d83cbc68810eaca20df1880334b5aeee`**. This equals the expected SHA after `git fetch`, with a clean worktree. |
| Ancestry | `a1d2ed4`, `16e96b0`, `bda6a3d`, `25cd2ed`, `e384794` on top of `16a248b` (the replay evidence). `7663229`, `c4827f9` and `46d84ad` are all ancestors. |
| Runtime tree | `reference/agentmem_ref` is **`f9ccd047…` at `e384794`, `16a248b` and `7663229`**. `pyproject.toml` is unchanged. The manifest's `system.revision` `16a248b` carries the identical runtime. |
| Adapter blob | `git hash-object` gives `9596099…`, equal to the manifest's `adapter.revision` and the committed blob. |
| Adapter source | Identical to the v6 adapter except the revision constant and the v7 tenant, actor, scope and purpose. |
| Configuration digest | **D1.** The v5 and v6 manifests both reproduce exactly under the basis their records state: `runtime_profile`, `public_contract`, `frozen_runtime_revision`, `tenant`, `actor`, `scope`, `purpose`. v7 used a different field set (`adapter_blob`, `runtime_commit`, `tenant`, `scope`, `public_contract`, `transport`) and gives `1c6adb53…`, where the recorded basis gives `0b0f366a…`. |
| Actual imported runtime | **D2.** Run as documented from the repository root, with an editable install of another checkout, the adapter imported `/home/user/agent-memory/reference/agentmem_ref`. That checkout's `runtime/adapter.py` differs from `16a248b`. The probe still completed 3/3, and the evidence claims `git-commit:16a248b…`. With `PYTHONPATH=<checkout>/reference`, all 47 modules the adapter loaded match `16a248b` blob for blob. |

**How the imported runtime was established.** A `sitecustomize` hook (`scripts/identity_capture_sitecustomize.py`) records the git blob of every loaded `agentmem_ref` file, in both the orchestrator and the stdio adapter process. Nothing in the system under test is modified. The records are in `identity/`, and `identity/tree_16a248b.txt` holds the comparison tree.

## 2. Contestant test and public Gauntlet run as submitted (step 2)

Everything ran from the repository root, with `PATH` set to the test venv and `PYTHONPATH=<identity hook>:<checkout>/reference`. CPython 3.13.16.

```
$ python -m unittest discover -s reference/tests -t reference -p test_644_v7_gauntlet_contestant.py
Ran 2 tests ... OK
$ agent-memory gauntlet validate-adapter examples/gauntlet/agent-memory-runtime-baseline-v7.json
Gauntlet adapter: valid
System: agent-memory-runtime-baseline-v7 @ git-commit:16a248b1e28f455fbf19217114175f0c20df2a01
Adapter: agent-memory-runtime-baseline-v7-stdio @ git-blob:9596099565bca72dfb177f6c00a5034453bd5593
Digest: 7c2ce709ab987fd217d6231c22e157446bf32a2ad2342b3cd0f50f1afb5937b3     rc=0
$ agent-memory gauntlet run --system examples/gauntlet/agent-memory-runtime-baseline-v7.json \
    --profile gauntlet-orchestration-retrieval-probe-v1 --allow-external-process --allow-destructive-reset --output-dir <dir>
Run: gauntlet-gauntlet-orchestration-retrieval-probe-v1-agent-memory-runtime-baseline-v7-c019ab3e22cf
Negotiation: eligible   Execution: complete   Authority effect: none   rc=0
```

I applied the workflow's own validation step (`runtime-baseline.yml`) with v7 identities to `runs/asis/`. Every assertion holds:
- qualification complete;
- the profile;
- stdio transport;
- manifest `baseline_id` v7;
- public facade only;
- normalized result complete;
- system id and revision;
- `baseline_or_probe`;
- `sample_count == 3` and **`exact_top1 == 1.0`** (cobalt, amber and cedar all top-1);
- authority none.

`provenance_class` is `unqualified_transition_probe`.

## 3. Defects and repairs (step 3)

| | Defect | Reproducer (`29d4b79`) | Repair (`b854d5e`) | After |
|---|---|---|---|---|
| **D1** | The configuration digest diverged from the basis stated in the v5/v6 records (`baseline-v6.json`, `configuration_digest_basis`). | `test_v7_digest_follows_the_recorded_basis` FAILs. `test_recorded_basis_reproduces_v5_and_v6` passes, as a control. | The digest is recomputed on the recorded basis: `0b0f366a…`. The candidate's own digest test asserts the same basis, which is stricter, because it reads the adapter's constants. Doc 82 is updated. | PASS |
| **D2** | No import provenance. A foreign or edited runtime is served and labelled with the frozen revision. | `test_foreign_runtime_is_refused_not_mislabelled` FAILs: `describe` answers `ok`. `test_own_checkout_at_frozen_revision_is_served` ERRORs. | **Fail-closed start-up guard.** The imported `agentmem_ref` must be this checkout's package, and its tracked files must equal `FROZEN_RUNTIME_REVISION` (`git diff --quiet`, nothing untracked). Otherwise every operation answers `runtime_identity_unverified`. `runtime_identity` is reported in `adapter_evidence`. The adapter blob is re-pinned to `2d650caa…`. | PASS |

**After the repair at `b854d5e`:**
- **Correct runtime:** `validate-adapter` reports valid; the run is **complete**, with every workflow assertion holding and `exact_top1` 1.0; all 47 loaded modules match `16a248b`.
- **Foreign runtime:** the run is **blocked** (rc 1) instead of mislabelled.

**Not repaired; recommended:**
- The orchestrator does not persist the adapter's `adapter_evidence`, so `runtime_identity` is absent from the evidence files. Completion now implies the guard passed, but a workflow or orchestrator step should record the `describe` identity explicitly.
- The **v6 adapter has the same import-provenance weakness**. It is frozen and published, so it is reported, not edited.
- `reference/agentmem_ref` is untouched: tree `f9ccd047…`, so **no re-declaration is required**.

## 4. Suite and checker (step 4)

| Command | Result |
|---|---|
| `python -m unittest discover -s reference/tests -t reference`, CPython 3.13.16, at `b854d5e` | **2688 tests OK** (skipped=25), rc=0, 182 s (`logs/full_py313.log`) |
| The same, with exactly pinned CPython 3.12.3 | **2688 tests OK** (skipped=17), rc=0, 182 s (`logs/full_py312.log`) |
| `-p test_644_v7_gauntlet_identity.py`, `-p test_644_v7_gauntlet_contestant.py` | 4/4, 2/2 |
| `scripts/check_runtime_baseline_equivalence.py --candidate <final SHA>` | TRANSITION: v6 to v7, frozen `e98e6e7` plus 8 declared blobs (run on the final evidence SHA, see the issue update) |
| `scripts/verify_644_v7_replays.py --reexecute` at `b854d5e` | 5 × VERIFIED. Acceptance: NOT GRANTED. |
| `scripts/check_644_v7_replay_inventory.py` | BLOCKED (exit 2), preserved |

## 5. What workflow-imported v7 evidence requires (step 5)

### Public Gauntlet

`runtime-baseline.yml` runs the Gauntlet only when the checker reports **PASS**. During a TRANSITION it prints "no evidence may claim … from this checkout".

Under docs/67, v7 Gauntlet evidence is produced on the **Step B1 publication PR**. That happens only after the declared tranche merges to `main`. At that point:
- the record's `runtime_revision.commit` is the main merge commit;
- the manifest's `system.revision` and the adapter's `FROZEN_RUNTIME_REVISION` must be re-pinned to that commit (with the repaired adapter, its identity guard then checks the same commit);
- the record states the configuration-digest basis.

Step B2 then binds the workflow run, artifact and digest. **No pre-publication workflow path exists**, so the local probe above is the most that can be produced now.

### AMB PrecisionMemBench and LongMemEval-S (D3)

The v7 declaration requires the lanes `amb-precisionmembench-retrieval-v6` and `longmemeval-s-retrieval-parity-v6`. `lane_gate_probe.py` (output in `lane-gate-probe.json`) applies the workflows' own preconditions and the importers' own `runtime_baseline_binding()` at this checkout:
- **both lanes are `accepted`.** `amb-competitive.yml` and `longmemeval-competitive.yml` assert `status == "frozen"`, so they **refuse to run them**.
- **both lanes pin the v6 declaration blob `1ac4d7d8…`.** The v7 declaration is `6e13cbae…`, so `import_amb_lane_evidence.py` and `import_longmemeval_lane_evidence.py` **refuse the evidence**.

docs/67 states it directly: "A successor needs new lane ids". **Required, as owner governance acts:**
1. Freeze new lanes, for example `amb-precisionmembench-retrieval-v7` and `longmemeval-s-retrieval-parity-v7`. Their control rows' `runtime_baseline_posture` names predecessor v6, successor v7, the final v7 declaration blob, and `checker_state_required: [PASS, TRANSITION]`.
2. Amend the v7 declaration's `acceptance_evidence_required` to name those lane IDs. Re-declaring changes the declaration blob, so freeze the lanes against the final blob.
3. Dispatch `amb-competitive.yml` (memory `agent-memory`, dataset `precisionmembench`, mode `retrieval`; no credentials) and `longmemeval-competitive.yml` (backend `agent_memory`, session and turn planes, full selection).
4. Import the evidence with the importers, and accept it in META_LEDGER.

**No Actions were dispatched here.**

### Credential-free local reproductions at `b854d5e`

These are not importable evidence:
- **AMB PrecisionMemBench, agent-memory row** (frozen AMB `03c1d0f`, constraints `8a7f4b9b…`): 15/77, active 4/43, precision 0.1806, recall 0.9535. **Per-query identical to the accepted v6 evidence**, and the cross-fact sidecar is byte-identical (`amb-compare.txt`).
- **LongMemEval-S**, 500 questions, input `d6f21ea9…`: session and turn planes, `agent_memory` backend, budget 50, CPython 3.12.3. Both runs returned rc=0. **The headlines equal the accepted v6 evidence; every metric and the per-question digest (`ranked_top`, metrics, `admitted_count`, status over 500 rows) equal the local v6 run; and governance equals the accepted v6 evidence** (`lme-compare.txt`).
  - Session: nDCG_any@10 0.878274, recall_all@10 0.892601; digest `7315db71…`.
  - Turn: nDCG_any@10 0.68156, recall_all@50 0.859189; digest `b6395fc2…`.
  - Output sha256: session `6734b22b…`, turn `0a433d49…`.

## 6. Boundaries preserved

- v6 is still the last published baseline. No register or record changed, and v7 is not published.
- The five replay fixtures are byte-unchanged, and the replay evidence re-verifies at `b854d5e`.
- No protected runtime change; tree `f9ccd047…`.
- Controller and recall authority are untouched; the adapter remains translation-only.
- No merge, no PR, no Actions, and no acceptance recorded.

## 7. Still required before formal v7

1. Independent acceptance of the replay evidence, recorded in META_LEDGER.
2. D3: new v7 lanes frozen, the declaration amended, workflow runs, imported evidence.
3. Step A merge of the tranche, then B1 publication with the repaired contestant re-pinned to the main merge commit, the Gauntlet workflow on that PR, then B2.
4. Decisions on F6, F7 and F12.
5. Adoption of `29d4b79` and `b854d5e` onto the implementation branch.
