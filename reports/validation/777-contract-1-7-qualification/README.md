# #777 contract 1.7.0 candidate: qualification and #776 integration reconciliation

| | |
|---|---|
| Candidate | `implementation/777-contract-1-7-successor-no-ci` @ `ada418c8e72da031e3900c1a4b252aacdcabb904` (verified; base: my reviewed redaction `541c09f`/`dc51da0`) |
| This branch | `validation/777-contract-1-7-qualification`: reports, an independent compatibility test, and integration patches. **No protected runtime change and no combined runtime is pushed.** |
| Integration trial | local-only scratch commit `345a778` (never pushed): `ada418c` plus the #776 memo fix plus six test-literal migrations; adapter blob `6567bdd6…` |
| Verdict | **CHANGES REQUIRED.** (1) The candidate's own full suite has **6 failures beyond the guards** (stale version literals). (2) It **inherits the #776 stale-cache defect** (P1). (3) The **draft declaration is not activatable** as written. The reconciliation is small and fully demonstrated below. |

## 1. Execution at `ada418c`
| Suite | Result |
|---|---|
| 4 new contract tests (`test_777_contract_1_7_successor.py`) | 4/4 |
| `test_api_contract.py` | 12/12 |
| All #777 tests (`test_777_*.py`) | 23/23 |
| Independent compatibility review (`test_777_contract_1_7_compat_review.py`, added here) | 4/4. Every 1.0.0–1.7.0 envelope is CURRENT with a **1.7.0** result (recall and history), and recall carries `public_projection` 1.0.0. 1.8.0 → `migration_required` with **no data fields**. All six schemas accept exactly 1.0.0–1.7.0. The result schema rejects 1.8.0. |
| Full reference suite | 2759 run, **11 failures** = the 5 expected (4 freeze guards plus durability) **plus 6 stale test literals** (`logs/full_suite_ada418c.summary.log`) |

**The 6 failures are versioning-only, not semantic:**
- **Probes that now mean "current":** `test_api_action_authority` and `test_api_surface` use `"1.7.0"` as the *future-minor* probe. Since 1.7.0 is now current, the probe must become `"1.8.0"`.
- **Pins to the old output:** `test_developer_facade`, `test_facade_recall_control`, `test_rc_cognitive_memory_scenario` and `test_typed_propositions` assert a `"1.6.0"` output.
- **Fix:** `integration/reconciliation_tests.patch` (test-only).

## 2. Inherited #776 defect (P1)
- `ada418c` carries `adapter.py` `50120369…`, which is #776 `5d90965`'s adapter (`6823eeaf`) plus the projection methods. It **predates** the memo-key repair (`fe25923f`).
- Running the #776 review tests against `ada418c`:
  - the decision-independence property **fails** (seed 4, step 21);
  - the query-order test **fails** (`live=True fresh=False`).
- The #777 projection's `public_identifier_withheld` uses the same `_deleted_lineage_reason`. A stale admission decision is therefore also a stale *projection* decision.

## 3. Exact reconciliation (demonstrated)
- **Three-way merge of `adapter.py`:** base `6823eeaf`, #777 `50120369`, #776 fix `fe25923f`. It merges **with no conflict** into a **single hunk**: the memo key gains `id(self._fact_memory), len(self._fact_memory)` (`integration/reconciliation_runtime_ada418c_to_integrated.patch`, 17 lines). The resulting blob is `6567bdd695c81a0f3f08c4b72b3ce70ce7d33263`.
- No other protected file differs between the branches' #776 parts. `surface.py`, `recall_control.py`, `contract.py` and the schemas come unchanged from `ada418c`.
- **Verification on the trial `345a778`:**

| Check | Result |
|---|---|
| #776 tests (33 plus the property test) | 34/34 |
| #777 tests | 23/23 |
| API contract tests | 12/12 |
| Full suite | 2767 run, **exactly the 5 expected** failures |
| Five corpora | Served lists **byte-identical** to #776 `5098577` (`runs/`) |

  Five-corpus figures (P0, answer@1, all-critical):

| Corpus | P0 | answer@1 | all-critical |
|---|---|---|---|
| Halcyon | 0 | 13/21 | 19/21 |
| Cedarline | 0 | 14/20 | 14/20 |
| Brightwater | 0 | 4/10 | 8/10 |
| Fenmoor | 0 | 9/12 | 12/12 |
| Blind theatre | 0 | 9/21 | 11/21 |

- **Required for an integrated candidate:**
  1. adapter blob `6567bdd6…` (the single memo-key hunk);
  2. the test-literal migrations;
  3. a corrected declaration (below);
  4. independent replay of that exact SHA.

## 4. Draft declaration review (`777-contract-1-7-v8-alternative.DRAFT.json`)
- **Blob check:** all 10 declared blobs equal `ada418c` exactly. The declaration validates against `runtime-baseline-declaration.schema.json`.
- **Disposable experiment** (draft registered as successor; never committed; `logs/checker_with_draft_registered_DISPOSABLE.log`). The checker **rejects** it for three reasons:
  1. **Chained successor:** "names predecessor v7 but the current baseline is v6". This is the same blocker reported for #773's draft v8.
  2. **Undeclared changes:** the six v7 files are reported undeclared, a consequence of (1), because the checker compares against published v6.
  3. **Out-of-boundary declarations:** the six `schemas/*.json` changes are reported as *"declared change absent from candidate"*. `schemas/` is **outside** the protected boundary (`pyproject.toml`, `reference/agentmem_ref`), so they must not be listed as protected changes. Record them as contract evidence instead.
- **Stale adapter blob:** after integration, the declared adapter blob must be `6567bdd6…`, not `50120369…`.
- **Identity delta:** `identity.public_contract_version` 1.6.0 → 1.7.0 is the right delta. The identity source is `api/contract.py:CONTRACT_VERSION`, and v6 records 1.6.0.
- **Evaluation exclusion:** `reference/agentmem_ref/evaluation/temporal_currentness.py` changed, but `evaluation/**` is an explicit non-runtime exclusion. Correctly not declared.

## Outstanding security risks
1. The P1 cache staleness persists until the reconciliation lands.
2. There is **no authorized audit reader** (#778). Detailed records are internal only.
3. **Residual linkable metadata:** `history.state_version` after re-creation, and global id-sequence gaps.
4. Competing post-v7 drafts (#773 and this one) must be reduced to **one** cumulative successor before any activation.

## Verdict
- **1.7.0 contract behaviour: PASS.**
- **Candidate SHA `ada418c`: CHANGES REQUIRED.**
- **Integrated path:** demonstrated, but **not qualified** until applied on a single candidate branch with a corrected cumulative declaration and replayed at its exact SHA.
