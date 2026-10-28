# Runtime Baseline v7 integration candidate: #836 cumulative runtime × #786 store profiles

**Status: INTEGRATION CANDIDATE, NOT QUALIFIED FOR PUBLICATION.** Nothing was merged, published, tagged or
promoted. No GitHub Actions run was dispatched, and every commit is `[skip ci]`. The live register is unchanged.
No baseline identity is claimed. Every result below was produced locally with CPython 3.12.3 and the pinned
`reference/requirements.txt`, on the commit named in each row.

The rules were preregistered in [`PREREGISTRATION.md`](PREREGISTRATION.md) before the integrated suite results were
inspected. Section 6 compares each preregistered outcome with the observed one.

## 1. Identities

| Item | Value |
|---|---|
| Integration branch | `integration/v7-786-836-reconciliation-no-ci` |
| #836 cumulative runtime (first parent) | `claude/cool-meitner-0q368g` at `f4386e2aad5f60a4a08e0d7faf9ec65dd1f6df8e`, protected tree `f9b5ff9e` |
| Security / store-profile branch (second parent) | `engineering/786-procedural-revocation-host-binding-20261027-no-ci` at `f3acce3bfaf9882c5e6517ecc53a23c8ae87f01d` |
| Merge base | `7d4c9be63d151a8b7272dea6b8beefd259f994e8` (published Runtime Baseline v6) |
| Integration merge | `3b778a3ad05e2442a0e40d613f0c6cae3786798a`. This is the runtime under test; the protected tree is unchanged after it. |
| Integrated runtime tree | `reference/agentmem_ref` `e9dce74b24f5941c4923402a8773433e22094a76` |
| Gauntlet re-pin | `f702bb2b674087c94bc52b8bed66110223250f38` |
| Evidence commits | `59b76aa6` (Gauntlet), `5e3c2fda` (A3, cross-check, verifiers) |
| v7 declaration blob | `06e33d935562e8a7e8587578f1c81fd7c019e9f8` (#836's was `7de94f11d7d521f07d2fe22317662ac6f92f89fa`) |

Neither source branch was modified. No historical fixture, frozen runner, freeze record or committed evidence folder
was edited. The superseded v7 lane rows were moved with `git mv` (section 5).

## 2. Reconciled protected source tree (27 declared blobs)

The Runtime Baseline checker at HEAD reports
`TRANSITION; baseline=v6; declared_successor=v7 (issue #674); frozen e98e6e7b + 27 declared blobs;
deltas=identity.public_contract_version 1.6.0->1.8.0` ([`check-runtime-baseline-equivalence.txt`](check-runtime-baseline-equivalence.txt)).
There is no undeclared delta.

**Reconciled by contract (3 files):**

| Path | Blob | #836 | security | Integrated rule |
|---|---|---|---|---|
| `api/surface.py` | `c9bfe7fa` | `ba8924d4` | `a62a330c` | #836, plus three additions: store-open contract 1.0.0 (profiles, exclusive identity claim, legacy single-project restriction, interrupted-creation completion), handle `task_ref`, and facade identity binding. Facade overrides and recall keywords may restate or narrow the handle's identity, never change it. #836's 1.8.0 malformed-scope refusal is checked first. The import of `RuntimeRecoveryError` is also fixed. |
| `runtime/adapter.py` | `89f3f6d7` | `2c0d3b6d` | `5a61fecf` | #836 (1.8.0 write-target authority, generations, #816 runtime-owned acts), plus the opt-in creator-principal ownership layer and `canonical_project_refs()`. Not carried, because they contradict 1.8.0: the security branch's refusal to reuse a deleted key, its lineage admission fence, `_unavailable_target_decision` and `history_eligible`. |
| `memory/procedural_memory.py` | `d7194e16` | `d5c25f43` | `3ca311f6` | #836 (`_visible_version`, scope kwargs), plus host-bound revocation. `revocation_context` is authoritative, and per-call kwargs are accepted only as an exact restatement. An unknown skill and a foreign skill get the same `ValueError`. |

**From the security branch, unchanged (6 files):** `api/store_contract.py` `83274c78`, `api/scoped_identity.py`
`378ac09f`, `runtime/revocation_delegation.py` `ff9922d8`, and their aliases `store_contract.py` `d7b506cb`,
`scoped_identity.py` `36c03894` and `revocation_delegation.py` `f41047fa`.

**From #836, unchanged (18 files):** #836's 21-blob set minus the three reconciled files, among them `api/contract.py`
`cadf9376`. Three of them supersede the security branch's edits to the same files: `runtime/recall_control.py`
`9fa861c3`, `runtime/runtime_composition.py` `11d1f4ec` and `runtime/query_driven_recall.py` `867d7f63`. #836's
#433/#835 scope-safe discovery is a strict superset of the security branch's prefilters.

Unprotected sources taken from the security branch unchanged: the A3 checker (`scripts/check_generalization_corpus.py`
`e2967b54`), the template source (`7cb95356`), the v2 Gauntlet adapters, `run_agentmembench_formal.py`, the mesa-v4
freeze and evidence, and the C7 harness.

## 3. Contract decision

- **Envelope contract `1.8.0`** (#836, owner-accepted 2026-10-22). Under ADR-030, `1.0.0`–`1.8.0` envelopes,
  including v6's `1.6.0`, stay `current`.
- **Store-open contract `agent-memory-store-open` `1.0.0`**, versioned independently. Store profiles, the identity
  record and the facade identity binding require only store-open 1.0.0.
- **Behaviour that genuinely requires 1.8.0:**
  - the refusal tokens `target_unavailable` and bare `fact_not_found`, and the non-disclosing results;
  - generation-relative versions, and re-creation of a deleted id as a fresh generation;
  - the #777 public deleted-lineage projection (1.7.0).

  None of these depends on the store-open contract, and nothing in store-open 1.0.0 depends on them.
- **Facade W4 (complete-scope host declaration through one handle).** Under store-open 1.0.0 the facade handle refuses
  an override that changes its identity. The module-level envelope surface keeps the exact 1.8.0 semantics. This is
  verified on a tenant-wide store by `FacadeIdentityBindingTests` in `tests/test_786_store_open_contract.py`.
  **Owner decision required** (section 7).

## 4. Baseline declaration status

`reports/runtime/baseline-v7-declaration.json` is one version-bound successor declaration:

- issue #674, predecessor v6;
- 27 blobs, written by `scripts/declare_runtime_baseline_changes.py`;
- identity delta `public_contract_version 1.6.0 -> 1.8.0`;
- 16 acceptance items: the union of #836's 13 and the security branch's `formal_replay:mesa-formal-v4` and the two
  `public_gauntlet` v2 successors.

The schema gains the `formal_replay` kind. `reports/runtime/baseline-register.json` is byte-identical to both sources:
v6 is the last published entry, and `declared_successor` names v7 by path. The integration does not change the
register. It does replace the content behind the pointer (blob `7de94f11` becomes `06e33d93`), which requires the
owner decision in section 7.

## 5. Test and evidence results (real runs)

| Run | Commit | Result |
|---|---|---|
| Full reference suite (pre-commit, staged merge) | tree of `3b778a3a` | 3376 tests. 20 failures and 2 errors, all bound to HEAD or to the frozen multi-project runners. All were reconciled below. |
| Full reference suite | `5e3c2fda` | 3382 tests: 2 failures and 1 error, all from three tests that resolve repo-root-relative paths and were started from `reference/`. Run from the repo root they pass, 14/14 ([`full-suite-5e3c2fda.txt`](full-suite-5e3c2fda.txt)). |
| Clean-clone verification (canonical repo-root invocation) | final head | [`clean-clone-verification.txt`](clean-clone-verification.txt) |
| Security-branch suites (`test_786_*`, `test_776_deleted_lineage_sqlite`) | integrated | pass (part of the full suite) |
| Oracle v2 (`security_falsifiers/test_786_store_profile_oracle_v2.py`) | integrated | 18/18 OK |
| Oracle v2 sensitivity | integrated | 8/8 must-detect detected. Three regressions name the #836 adapter's equivalent defence. |
| Store-open contract sensitivity | integrated | 7/7 must-detect detected |
| A3 re-gate sensitivity | integrated | 53/53 must-detect mutations killed |
| A3 re-gate evidence | `59b76aa6` | all checks hold; checker and template blobs are the audited ones ([`a3-regate-evidence-59b76aa6.json`](a3-regate-evidence-59b76aa6.json)) |
| Legacy collision oracle v1 (historical) | integrated | `StoreIdentityError` at the second project, identical to `f3acce3b`; this is the retired interface |
| Replay cross-check (non-recording) | `59b76aa6` | **10/10 families reproduce the committed #836 observation digests** with only the frozen runner's opener routed to the tenant-wide fixture ([`replay-crosscheck-59b76aa6.json`](replay-crosscheck-59b76aa6.json)) |
| `verify_786_security_replays.py` / `verify_644_v7_replays.py` on #836 evidence `2ad4cf23` | `5e3c2fda` | 10/10 **STALE**, for "runtime files differ from the evidence source commit" alone; otherwise untampered |
| the same with `--reexecute` (default profile) | `5e3c2fda` | 5 STALE. The other 5 differ on re-execution, because the default `single_project_v1` profile stops their runners at the second project. The verifier labels this `TAMPERED`, but the committed bytes are untampered. |
| v2 Gauntlet successors (`run_gauntlet_v2_successor_evidence.py`) | `f702bb2b` | both QUALIFIED: two real runs each, inputs clean (`reports/gauntlet/agent-memory-public-v2-successors/local-qualification.json`) |
| v7 orchestration retrieval probe | `f702bb2b` | `complete`, 3/3 exact top-1, transcript equal to #836's probe at `4fb11a59` modulo identity and timing. The source-mismatch control is `blocked` (`runtime_identity_unverified`) ([`gauntlet-probe-f702bb2b/`](gauntlet-probe-f702bb2b/)). |

**Cross-branch regression found and fixed.** Oracle v2's canonical-gate probe called `governed_delete` outside a
runtime generation. Under #816 both the foreign id and the absent id raised the same `UngovernedDurableWrite`, so the
comparison held vacuously on the integrated tree, and the oracle missed a disabled writer-eligibility gate. The probe
now runs inside `run_governed_read`, and asserts that no exception was raised before it compares.

**Test reconciliations (each against the preregistered rules):**
- Multi-project #836 tests open the test-only tenant-wide fixture (`tests/_tenant_wide_fixture.py`). Tests premised on
  caller-declared cross-scope authority use its host-declared mode.
- Frozen #786/#809/#644 replay runners keep their bytes. Only their `AgentMemory` opener is routed to the fixture
  (`frozen_runner_store`). `tests/test_v7_integration_frozen_runner_profile.py` records that the default profile stops
  them, and that the same case passes when only the opener changes.
- Security-branch tests take the 1.8.0 tokens, composition and generation re-creation.
- The v1 Gauntlet contestant tests classify v1 as stopped by the store profile. Their qualification assertions now run
  against the v2 successors.
- `test_770` freshness now asserts the exact invalidation.

## 6. Preregistered vs observed

| # | Preregistered | Observed |
|---|---|---|
| 1 | Security suites pass with only the listed reconciliations | as predicted. One addition: the oracle v2 probe repair above, which is a test-harness defect exposed by #816, not a rule change. |
| 2 | #836 suites pass, except caller-declared cross-scope premises | as predicted. The reconciled tests are listed in section 5. |
| 3 | #786 families reproduce, except facade W4 | **Deviation, disclosed.** On formal re-execution with the default profile, the multi-project cases of four families stop at the opener (12/13, 3/10, 5/8 and 11/13 cases), so their observations cannot be reproduced. The cross-check, with a tenant-wide opener that restores 1.8.0 override semantics, reproduces all five, W4 included. W4's integrated facade behaviour (refused) is therefore covered by `FacadeIdentityBindingTests`, not by a replay. A re-preregistered W4 replay generation is required. |
| 4 | #644 replays reproduce | Cross-check: 5/5 identical. On the default profile, `governed-persisted-typed-slot-sufficiency-admission-recheck-v1` cannot run its multi-project cases (A6 and two others). |
| 5 | Probe and both v2 successors green after re-pin; v1 refused | as predicted |
| 6 | Full suite: only v1 contestant tests and re-pin guards fail | the pre-commit run matched this, plus the frozen-runner opener and HEAD-bound evidence checks. The final run is in section 5. |

## 7. Evidence invalidated by the integrated tree (fresh qualification required)

Nothing below was deleted or rewritten. Each item stays valid for the tree it names.

1. **#786 / #809 / #835 security replay evidence.** `cross-scope-write-authority-denial-v3`,
   `deleted-lineage-generations-and-restart-v3`, `public-tombstone-redaction-and-observer-separation-v3`,
   `evidence-reference-authorization-v1` and `scope-safe-graph-discovery-v2`, at
   `674-cumulative-candidate/security-replays-2ad4cf23…`. The first four need a new, preregistered replay generation
   (DSL successor) that opens scope-distinct stores. W4 is re-preregistered as refused at the facade.
2. **#644 replay evidence** at `674-cumulative-candidate/644-v7-replays-2ad4cf23…`. All five need re-recording on the
   integrated tree. `governed-persisted-typed-slot-sufficiency-admission-recheck-v1` needs a runner generation for
   scope-distinct stores.
3. **v7 lanes.** `amb-precisionmembench-retrieval-v7` and `longmemeval-s-retrieval-parity-v7` are re-pinned to
   declaration `06e33d93`. The `f9b5ff9e` rows are under `superseded-836-tree-f9b5ff9e/`. Both lanes must be executed
   again in full; the AMB harness checkout and the LongMemEval_S dataset are not present in this environment.
4. **mesa-formal-v4.** It is pinned to contract 1.6.0 and tree `eafa528f`. The integrated contract is 1.8.0, so a new
   owner-authorized freeze is required before the `formal_replay` item can be met.
5. **Gauntlet.** The local records at `f702bb2b` are pre-publication evidence. Publication evidence must come from the
   repository workflows at the published revision.
6. **A3.** Re-checked at `59b76aa6`, and the checker is unchanged. It needs only the independent reviewer's verdict on
   this revision.

## 8. Owner decisions required (none recorded here)

1. Adopt the integrated declaration content (`06e33d93`) as the v7 successor behind the existing register pointer.
2. Facade W4: accept that a facade handle refuses identity-changing overrides (store-open 1.0.0), while the envelope
   surface keeps 1.8.0.
3. #809 legacy upgrade: store-open 1.0.0 gives a multi-project legacy store no supported upgrade path. It is refused
   for every project and left untouched. Decide whether a migration path is in v7 scope.
4. #839 / #840 / #841 and the post-v7 combined preview. Each is stacked on older #836 commits (`72d6a903`, `ab4e549d`),
   and each conflicts with the integrated head in `api/surface.py` and `scripts/restructure_package.py`. #840 overlaps
   `_atomic_write_text` (exclusive creation, symlink hardening) and the host-activation guard. They are not integrated.
   Each needs a rebase and its own successor declaration after v7.
5. Authorization for the replay successor generations, the lane re-execution and the mesa-formal-v4 refreeze.

## 9. Remaining publication gates

- The owner decisions in section 8.
- Fresh qualification of every item in section 7.
- Independent review of the reconciled protected files, the oracle repair and the test reconciliations.
- Hosted CI and the repository Gauntlet/benchmark workflows at the candidate revision. These were not run, by
  instruction.
- Merge, the register update and the v7 publication record. These were not done, by instruction.
