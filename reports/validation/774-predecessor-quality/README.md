# #774 Governed historical predecessor targeting: implementation and held-out measurement

| | |
|---|---|
| Implementation branch | `implementation/774-governed-predecessor-targeting-no-ci`, from the frozen v7 parent `9b025f945e7ec4a1e349e56bba251e3122413e88` (isolated from #773 and #775) |
| Failing tests | `c077628` (12 tests: 15 errors with the method absent; 1 pre-existing expected failure) |
| Implementation | `ce1fdfc` |
| Protected blobs | `runtime/adapter.py` `7aba1ffe…`, `runtime/runtime_composition.py` `48d936b7…` |
| Validation branch | `validation/774-predecessor-quality`; uses the v3 provenance runner from `evaluation/771-lifecycle-v3-provenance-no-ci` |
| **Slice verdict** | **CHANGES REQUIRED.** It works and improves served quality on held-out data with no privacy regression. Before merge it needs a successor declaration, automatic routing measured separately, and a guard against wrong-subject anchoring. |

No Actions, no PR, no merge, no baseline change. The v7 declaration and register are unchanged.

## What was built (storage and admission architecture, no lexical heuristics)

**`GovernedMemoryAdapter`** (read-only helpers):
- `governed_state_change_predecessor(fact, ctx)`:
  - walks the fact's logical memory (`_fact_memory`) backwards in governed write order;
  - **skips versions replaced by an error correction** (they never held);
  - returns the first version replaced by a **state change**, but only if **canonical historical admission** (`_admission_refusal(..., historical)`) admits it to this reader, which enforces tenant, project, task, purpose, tombstone and dispute rules;
  - otherwise returns nothing, and never falls back to an older version;
  - deleted memories and inconsistent or physically removed lineage yield nothing.
- `lineage_visible`, `lineage_head` (the current version of a memory, if visible and not deleted), and `memory_deleted`.

**`ConfiguredCompositionRuntime.historical_predecessor_context(query, ctx, budget, successor_ref=None)`**:
- The caller declares the relationship by calling it. **Nothing is inferred from query wording.**
- Historical recall runs unchanged.
- The anchor is the declared successor (which must be visible, else `ValueError` with the same message for unknown and hidden refs), or else the **current version** of the highest-ranked lineage-bearing memory.
- **Exactly one item, the predecessor, moves to rank 1**; all others keep their governed order.
- Versions of deleted memories are never served by this method.
- The result carries `relation="immediate_state_change_predecessor"` and has no causal, explanation, completeness or authority fields; all are validated.

## Tests

| Suite | Result at `ce1fdfc` |
|---|---|
| `test_774_governed_predecessor.py` | 12/12, plus 1 expected failure (pre-existing, below) |
| 13 related temporal/admission/ranking/currentness suites | all OK |
| Full reference suite | 2722 run, 5 failures, plus 1 expected failure. 4 are the protected-runtime freeze guards, the intended consequence of an *undeclared* protected change. 1 is the durability `adapter_eof`, which also fails on the v7 parent and on main. No other failures. |

The preregistered tests use generic 2-, 3- and 5-revision histories (kiln glaze, tram timetable, catalogue engine, sensor rate, CI host). They are not holdout wording. Two genuine design corrections came out of them:
1. **Plain historical recall still ranks a deleted memory's old version**, so the opt-in path now filters deleted memories itself.
2. **Anchoring on the top-ranked version** could pick an *older* version and return *its* predecessor. The anchor is now the memory's current head.

## Pre-existing P0 found (v7, not changed here)

**Governed deletion tombstones only the current fact.** Earlier versions of a deleted memory stay admissible to **plain historical recall**:
- Pinned as `expectedFailure` in `PreExistingDeletionLeak`.
- On the held-out corpus, the unchanged v7 path **served `meter-arq`** (a version of the deleted meter memory) for B05.
- #774's routed path does not serve it.
- The fix belongs in admission (tombstone by logical memory or by version chain) and needs its own slice and successor declaration.

## Served quality at the actual budget (v3 runs with separated provenance; same instant T)

Routing (which questions the caller declares as predecessor requests) was **frozen before any #774 run** (`holdout/routing-declarations.json`). Brightwater was authored and frozen (`cbf03d0`) before #774 ran on it, and was not used to design the logic.

| Corpus | Variant | P0 prohibited / stale | Answer@1 | All critical | No-answer with context (items) | Precision / recall @b | nDCG@b |
|---|---|---|---|---|---|---|---|
| **Brightwater v1 (held-out)** | v7 composed | **1** / 0 | 4/10 | 8/10 | 2 (4) | 0.467 / 0.850 | 0.748 |
| | **#774 routed** | **0** / 0 | **8/10** | **9/10** | 1 (3) | 0.500 / 0.900 | 0.872 |
| | #774 over-routed | 0 / 0 | 7/10 | 9/10 | 1 (3) | 0.500 / 0.900 | 0.826 |
| Halcyon v1.1 | v7 composed | 0 / 0 | 13/21 | 19/21 | 3 (9) | 0.444 / 0.905 | 0.826 |
| | **#774 routed** | 0 / 0 | **15/21** | 19/21 | 3 (9) | 0.444 / 0.905 | 0.841 |
| Cedarline v1.1 | v7 composed | 0 / 0 | 14/20 | 14/20 | 4 (8) | 0.475 / 0.767 | 0.765 |
| | **#774 routed** | 0 / 0 | **16/20** | **16/20** | 4 (8) | 0.508 / 0.817 | 0.831 |
| | #774 over-routed | 0 / 0 | **13/20** | 16/20 | 4 (8) | 0.508 / 0.817 | 0.777 |

**Default stability:** the #774 head's default composed recall is **byte-identical to v7** on all three corpora.

**Per question (routed):**
- **Improved:**
  - **B01** (3 revisions): predecessor to rank 1.
  - **B02**: correctly skips the error-corrected 0.8 → 0.5.
  - **B03** (5 revisions): the predecessor was not served at all before; now rank 1.
  - **B04**: the predecessor now outranks the rationale memory, which stays in context.
  - **H02, H14**: rank 2 → rank 1.
  - **C02, C07**: the predecessor was outside the budget before; now rank 1.
- **B05** (deleted memory): baseline P0 exposure → withheld.
- **No change:** C15 (already rank 1).
- **Remaining failures:**
  - **B11**, a no-safe-answer question about an other-project budget. The selector anchored on the unrelated home "pumps" chain and promoted `pumps-3`. Nothing prohibited was served, but this is **wrong-subject targeting**.
  - **B12**, the predecessor of an *older* version ("before Ignition 8.0"). The selector answers relative to the current version, so it stays a miss. This needs a target from routing, `successor_ref`, or as-of intent.

**Over-routing harm** (if every historical question were routed): rank 1 is lost on C12, C13, C18 and B06, and Cedarline answer@1 falls *below* baseline (13/20). **Correct routing is essential; automatic routing must be built and measured as its own step**, as #774 step 4 specifies.

## Remaining limitations

1. Routing is caller-declared. No natural-language coverage is claimed.
2. Wrong-subject anchoring (B11): when the asked subject isn't visible, the highest-ranked lineage memory may be unrelated. Candidate mitigation: require the anchor to be among the top-k *admitted* candidates and fall back to unchanged ranking otherwise; measure it.
3. Predecessor-of-older-version requires a declared successor or an as-of instant.
4. "Why" questions are untouched by design. The method never attributes causes.
5. The selector shares `runtime_composition.py` with #773, so a combined candidate needs merge review. **Do not combine them into one baseline.**
6. Brightwater was written by the same reviewer who wrote the #774 logic. It is held out from design, but not blind.
