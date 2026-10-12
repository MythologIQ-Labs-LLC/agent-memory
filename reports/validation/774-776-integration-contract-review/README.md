# #774 × #776 lineage integration contract: execution and integration design

| | |
|---|---|
| Contract branch | `evaluation/774-776-lineage-recreation-integration-contract-no-ci` @ `38a682305fc90c743ddc81733f1759f75c58676f` (verified; uncombined #774 runtime `a6745a9`) |
| This branch | `validation/774-776-integration-contract-review`. **Reports and artifacts only; no protected runtime is changed or combined on any pushed branch.** |
| Design prototype | local-only commit `b367b76` (never pushed) = `cc13930` + the #774 runtime diff + the design delta. It exists only to execute the design. The patches are in `design/`. |
| Verdict | Contract **validated** (detects the conflict; no fixture defect in the four tests). The fact-level design **passes** every contract, #774, #776 and adversarial generation test, and preserves #774's measured quality. **Not a merge candidate.** It needs a successor declaration, an independent review of the design and the C3 fix from the #776 adoption review. |

## 1. Four preregistered tests on the uncombined #774 (`38a6823`)
| Test | Result | First failing assertion | Diagnosis |
|---|---|---|---|
| T1 new generation visible after the prior lineage is pruned | **FAIL** | line 31, old version admitted to historical recall | Per-assertion probe (`design/contract_t1_per_assertion_probe.py`): A1 new head admitted ✓; A2 old lineage withheld ✗ (the pre-existing #776 leak, since #776 is absent); **A3 `memory_deleted(new)` is True ✗; A4 `lineage_head(new)` is None ✗** (the memory-ID-wide check). The A2 failure masks the intended A3/A4 failure. This is not a fixture defect. |
| T2 new generation cannot inherit the deleted generation's predecessor | pass | – | Passes for the **wrong reason**: the memory-ID-wide guard returns no predecessor for *any* fact of a re-used ID. |
| T3 deleting a superseded version keeps the current target | **FAIL** | line 75, `memory_deleted(current)` is True | Exactly the intended architectural conflict |
| T4 other memory unaffected by the re-used ID | pass | – | Control |

**Naive combination** (`cc13930` plus the #774 diff, applied cleanly, memory-ID-wide checks unchanged): T1 fails at **line 35** (`memory_deleted(new_generation_head)` is True; the old lineage is now correctly withheld) and T3 at line 75. #774's `PreExistingDeletionLeak` becomes an *unexpected success*. **This shows directly that memory-ID-wide tombstone checks cannot coexist with #776 re-created lineages.**

Fixture defects: none in the four contract tests. One defect was in **my own** design test helper: a correction's `state_snapshot` must name the current version, which caused a `stale_authorization` refusal. It was corrected before the design results below.

## 2. Integration design (canonical fact-level lineage and admission visibility)
`design/design_delta_over_naive_combination.adapter.patch` (46 changed lines in #774's adapter helpers only):

1. **`memory_deleted(fact)`** is the canonical fact-level decision, the same one admission and `write_semantics` use (`_deleted_lineage_reason`). A physically erased fact counts as deleted iff a deletion record covers it. There is no `tombstoned_ids()` / memory-ID test.
2. **`lineage_head(fact)`:** None if the fact is in a deleted generation. Otherwise the memory's current fact, which must itself be live and admission-visible. A live fact's head is necessarily in the same live generation.
3. **`governed_state_change_predecessor`:**
   - Walking back in write order, **any deleted fact is a barrier**: return None. The walk never crosses into a deleted generation and never skips a deleted superseded version to an older one.
   - **Erased whole generations** (members of a *head* deletion record, i.e. a key with no replacement record) are dropped from ordering, because re-creation always follows them.
   - An **erased superseded version** fails closed (no predecessor), because its position cannot be placed.
4. A declared successor that is deleted, unknown or out of scope raises the identical `ValueError` (no ID leak).

## 3. Design verification (prototype `b367b76`)
| Suite | Result |
|---|---|
| 4 contract tests | 4/4 |
| `test_774_governed_predecessor` (with `PreExistingDeletionLeak` **without** `expectedFailure`) plus anchor/routing | all pass |
| 23 #776 tests | 23/23 |
| 7 adversarial generation tests (`design/test_774_776_integration_design.py`): second-generation history, deleted superseded version not skipped, deleted successor refused like unknown, error correction inside the new generation, **restart**, **erased old generation does not block the new generation**, **erased superseded version not skipped** | 7/7. On the naive combination 3 fail; the erased-generation case also failed my first design draft and drove change 3. |
| Full reference suite (serial) | 2767 run, 5 failures = 4 freeze guards plus durability `adapter_eof`. An earlier concurrent run showed 3 extra replay-evidence failures that were run interference; they pass serially. |

**Quality (v3 harness, evaluator `9961067`; `design/results-prototype-four-corpora.json`).** Declared and automatic served lists are **byte-identical to the #774 head `a6745a9`** on Halcyon, Cedarline, Brightwater and Fenmoor (Halcyon 15/21, Cedarline 16/20, Brightwater 8/10 declared, Fenmoor 12/12 declared). The default composed path now has P0 = 0 on all four (it includes #776).

## Not done here
No combined protected candidate is proposed. A combination additionally needs:
- the #776 C3 transitive-derivation fix (`validation/776-adoption-qualification` @ `42c218a`);
- an independent review of this design;
- a sanctioned successor declaration;
- explicit approval.
