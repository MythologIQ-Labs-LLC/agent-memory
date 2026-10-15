# Independent adversarial review of C3 (head `4356a550`, base `3179ffa5`)

A separate review agent worked read-only against the worktree. It was barred from the sealed
held-out cohort and from benchmark answer files. Its repro scripts are summarised here, and each
finding is pinned by `reference/tests/test_c3_review_regressions.py`. Seven of those ten tests fail
on `4356a550` and pass after the repair. The other three are bounds or equivalence checks.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | blocking | `ranked_prefix` no longer reproduced pre-C3 behaviour. Discovery expansion ran for every recall and changed candidates, `admitted`, rank order and the lexical route score. Natively on LongMemEval-S, 11 of 500 `ranked_prefix` lists differed from A. | **Fixed.** Expansion (and the query reading it needs) runs only under `relevance_sufficient`. The lexical route score is the overlap with the query as written (0 for a fact found only through a variant). `ranked_prefix` is exactly 1.4.0. |
| 2 | blocking | The #583 anti-laundering mask was computed on raw tokens while relevance compared normal forms. A self-claiming fact with "planned" escaped the mask for a "planning" query and was returned. | **Fixed.** The mask is matched on normal forms (`_normal_form_masks`), with the same eligibility and self-claim rules as the ranking stage. |
| 3 | should-fix | Text that admission refuses (derived from a forgotten source, disputed) stayed in the discovery vocabulary. It changed expansion counts and turned typo correction off. | **Fixed.** The vocabulary uses `discovery_admissible`, which applies current-state admission's identity checks: tenant, tombstone (per fact), derived-from-tombstoned source, event-invalid, dispute, domain. |
| 4 | should-fix | Lifecycle closure followed relations the #550 interpreter derives from plain text. That contradicted the documented "never memory text". | **Fixed.** Closure follows typed relations only (caller-declared or extracted propositions). Docs and tests now state this. |
| 5 | should-fix | Query interpretation was quadratic in query length (16,000 words: 21 s), ran twice, and also ran on `ranked_prefix`. | **Fixed.** A linear `starts_sentence` replaces the per-word regex over the prefix. It is proven equal to the regex on 319,083 random prefixes, including the `$`-before-newline case. Interpretation is memoised (16,000 words: 0.05 s) and is absent from `ranked_prefix`. |
| 6 | should-fix | Entity coverage did one BM25 pass per mention, so letter–digit identifiers made it O(mentions × admitted). | **Fixed.** At most 8 mentions are covered (`MAX_COVERED_MENTIONS`), and rank positions are precomputed. |
| 7 | should-fix | A memory re-remembered under a forgotten reference never entered the vocabulary (it failed closed). | **Fixed** by #3: tombstones are checked per fact uuid, not per memory id. |
| 8a | note | Per-recall vocabulary cost grows with store size. | **Accepted, measured.** About +18 ms at 3,000 facts with no candidates; see the slice 2 record. |
| 8b | note | Stale docs (policy version, "no morphology", "as written"). | **Fixed** (docs/44, the `recall` docstring). |
| 8c | note | Typo tolerance can replace an abstention with a near-miss fact, and an in-scope writer could plant one-edit neighbours. | **Accepted, recorded.** It is guarded: only short queries whose topic matched nothing, terms of five or more letters, and in-scope admissible text only. It is a quality risk, not an isolation one. |
| 8d | note | Historical recall gets no expansion from superseded text. | **Accepted.** That follows from the admissibility rule; current-only vocabulary is the safe default. |
| 8e | note | Closure accepts a change whose `replaces_value` differs from the target's value. | **Pre-existing #671 semantics, recorded.** Typed-slot relations do not compare `replaces_value`. A follow-up candidate for #671. |
| 8f | note | **The ranking-anchor change was diagnosed on LongMemEval-S gold traces.** | **Disclosed.** `scripts/lme_trace.py` reads gold labels to attribute returns to selection bases. The anchoring change (2.1.0) was motivated by that trace: 1,056 `ranked_above_sufficient` returns, 14 of them gold. The runtime has no dataset vocabulary, identifiers or answer rules. LongMemEval numbers in these records are diagnostic, not holdout evidence. |
| 8g | note | `expansion_terms` had an unused `skip` parameter. | **Removed.** |

Attacks that held:
- **Isolation:** out-of-project text does not affect anything.
- **Lifecycle:** forget, correct and permanent delete stop text shaping expansion in the same
  handle and after reopen. Closure never adds a non-admitted fact. Multi-cardinality, other
  subject, earlier clock, negation, self-claim and other-actor relations do not close.
- **Determinism and contract:** selection is always a ranked subsequence. Outputs are identical
  across `PYTHONHASHSEED` values and reopen.
- **Robustness:** 79 edge queries caused no crash and no schema failure.
- **Memo lifecycle:** the per-uuid memo is sound.
