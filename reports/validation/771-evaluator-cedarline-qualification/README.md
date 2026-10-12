# #771 Evaluator qualification, Cedarline evaluation and generalization

| | |
|---|---|
| Evaluator | `evaluation/served-memory-quality-first-no-ci` @ `73030db8498c2f94d177ab1d52bebbc91242dab6` (verified) |
| Cedarline corpus | `evaluation/771-cedarline-second-holdout-frozen-no-ci` @ `32404f7e0c800110cf7a72ba128479afc8bf0d83` (verified) |
| Halcyon v1.1 | `validation/771-served-memory-quality-cloud` @ `04543a79…` (digests unchanged since freeze) |
| Validation branch | `validation/771-evaluator-cedarline-qualification` (forked from the exact evaluator SHA) |
| Environment | Claude Code cloud, Linux, Python 3.13.16, `reference/requirements.txt`, full clone; no GitHub Actions, no PR |
| **Evaluator qualification verdict** | **CHANGES REQUIRED (minor)**: E1–E5 verified as adopted; adopt R-A1 (label integrity, repaired here). Two documented limitations remain. |
| Companion runtime review | #773: `validation/773-current-context-selector-review`, runtime verdict **CHANGES REQUIRED** |

**Independence disclosure.** The adopted evaluator commit (`73030db`) is byte-identical to the repairs I authored in the previous qualification. Phase A is therefore partly a self-review. To compensate, I added seeded property checks that do not reuse my example tests. I also found and fixed a defect in my own lifecycle qualifier (R-A1).

## Phase A: evaluator adoption

| Check | Result |
|---|---|
| Top-level served-memory suites at `73030db` | 48 OK + 6 expected failures (runtime-gap reproductions) |
| Previously disabled provenance tests | **all 11 execute and pass** |
| Integration suite (`test_771_served_memory_integration.py`) | 8/8 OK |
| E1–E5 property checks, 6 properties × 300 seeded trials (`tests/test_served_memory_properties_771.py`) | all hold |
| Final suite on this branch | 55 OK + 6 expected failures |

What the properties verify:
- **E2:** emptying an answerable case never raises macro precision.
- **E3:** adding no-safe-answer cases never changes answerable P1 or P2 metrics.
- **E4:** recall at budget lies in [0, 1] and reaches 1.0 for an ideal context.
- **E5:** `top1_critical` is true iff rank 1 is critical, implies `top1_relevant`, and support-only rank 1 does occur.
- **Abstention:** never inferred, on any random run.
- **Unsafe memories:** stale or forbidden memories never earn precision or rank-1 credit.

**Remaining defect, failing test first (`96ccff8`) → repair (`f86e173`):**
- **R-A1: lifecycle gold could credit an error-corrected value.** An error correction declares the old value never true, and the runtime refuses it as `corrected_as_false` for every intent. Yet the qualifier accepted gold making it the critical answer to a historical question, which is precisely how the Halcyon v1 encoding error went undetected.
- `lifecycle_facts` now reports `error_corrected`, and the qualifier refuses gold that grades one ≥ 2 and eligible for any intent.
- The shared lifecycle test fixture modelled a state change as `correct`; it now uses `update`.

**Documented limitations (not fixed):**
- **R-A2:** lifecycle inputs carry no declared evaluation instant. The runtime's deterministic clock (2026-01-01 plus ticks) is the implicit "now". Comparisons that need an instant must supply it explicitly, as the Phase D adapter does. Recommend an optional `reference_time` in a future input schema version.
- **R-A3:** run manifests record the evaluator checkout's `HEAD` as `runtime_revision`. These are the same tree today, but for cross-checkout comparisons the adapter records the runtime root SHA and `runtime_composition.py` blob separately.

**Lifecycle runner change:** `build_store()` was extracted from `run_scenarios()`, with no behaviour change. Default composed outputs equal the CLI runs exactly.

## Phase B: Cedarline review and execution

**Frozen identity:**
- All five documented blob IDs match (`b08e05d3…`, `1da8e7eb…`, `93e4ddc1…`, `9c652444…`, `54b00f62…`).
- The v1 → v1.1 amendment changes **exactly** `queries[10].query` and `cases[10].scenario` (C11 wording), as documented.
- v1 is preserved.

**Independent label review, before any execution** (no gold was changed):
- **Factually and temporally consistent.** Updates are state changes. The offset chain 2 mm → 5 mm (update) → 3 mm (correct) correctly makes 5 mm error-corrected, and it is graded 0 everywhere, so the corpus passes R-A1. Stale sets match lifecycle and the expired 2025-12-01 window for current intent. Prohibited sets cover deleted, other-project and other-tenant memories. Graded alternatives are sensible ("immediately before Delta Lake": Parquet 3, Delta 2, CSV 0).
- **Taxonomy concern.** `offset-5mm-bad` is in **prohibited** as well as stale. Serving it would be scored as a P0 *access* breach although it is a temporal-correctness error, which overstates privacy failures. It was never served in any run, so there was no measured impact.
- **Strictness notes:**
  - C24 has budget 3 for exactly 3 required facts (zero slack).
  - C11 v1.1 grades the expired freeze 0 rather than context.
  - The prohibited sources in C22/C23 are graded 0; this has no scoring effect.
- **Not blind.** Cedarline was authored after Halcyon's failure classes were public. It is evidence of reproduction across domains, **not** independent proof of generalization.

**Execution:** the plan's CLI, from the clean exact corpus SHA, with a fresh SQLite store per backend (`cedarline-v1.1-cli-runs/`, `input_sha256 = b943fbc1…`).

| Cedarline v1.1 (20 answerable, 4 no-safe-answer) | composed-multiroute | governed-lexical |
|---|---|---|
| P0 prohibited exposure | **0** | **0** |
| P0 stale exposure (cases) | 1 (C11: expired freeze at **rank 1** for "currently in effect") | 0 |
| P1 answer at rank 1 | 0.700 (14/20) | 0.550 |
| P1 all critical evidence served | 0.700 | 0.550 |
| P1 empty context on answerable | 0 | 0 |
| P1 no-safe-answer questions given context | 4/4 (8 memories) | 4/4 (8) |
| P2 precision / recall @budget | 0.475 / 0.767 | 0.367 / 0.608 |
| P2 nDCG @budget | 0.765 | 0.603 |
| P2 distractors served | 34 | 41 |

The per-question tables for both corpora and every variant are in **[`PHASE_BD.md`](PHASE_BD.md)**, generated from `phase-d-results.json`.

### Do Halcyon's weaknesses generalize? (unchanged runtime, mechanical category rules)

| Category | Halcyon v1.1 | Cedarline v1.1 |
|---|---|---|
| Stale exposure for current intent | H09 | C11 |
| Context served with no safe answer | H17, H18, H19 (3/3) | C11, C21, C22, C23 (4/4) |
| Historical question, answer not at rank 1 | H02, H04, H14 | C02, C03, C04, C07 |
| "Why" question, answer not at rank 1 | H04, H12, H23 | C03, C04 |
| Multi-fact question incomplete | H20 | C13, C20, C24 |
| Unconfirmed claim at rank 1 | H22 | C14 |
| Current question, answer not at rank 1 | H01, H20, H22 | C14, C17 |

**Every Halcyon failure class reproduces in a different domain**, written by a different author, with zero prohibited exposure on either corpus.

In Cedarline the predecessor is often **not served at all**: C02 Parquet at rank 7 and C07 Survey Operations at rank 4, both at budget 3. Halcyon's predecessors were at rank 2. This is consistent but not blind evidence. A fresh, blind holdout is still required before any global claim.

## Phase D (summary; detail in `PHASE_BD.md` and the #773 report)

- Default recall is **byte-identical** on main (`3eebb6d`), the v7 parent, the #773 candidate and the #773 repair. That holds for served rows and full ranked admissions, on both corpora.
- With the same instant `2026-10-12T12:00:00Z`, the v7 composed path and the #773 selector serve **identical** contexts on every question, on both corpora.
- Stale exposure drops from 1 to 0 on both corpora **because the instant reaches the existing ranking policy**. The selector's own exclusion changed no served item. One distractor replaced the stale item on each corpus, so P1 and P2 are unchanged.
- No valid evidence was excluded on either holdout. On new "still in effect?" probes the selector withheld the answering evidence; this is repaired in #773 as D773-2.

## Phase E: next implementation slices (evidence-based)

### G6: historical target specificity, as governed lineage rather than chronology or similarity (`g6-lineage-analysis.json`)

- In **4 of the historical misses** (H02, H14, C02, C07) the asked-for memory is the governed **state-change predecessor** of a memory ranked above it in the same logical memory chain. It sat at ranks 2, 2, 7 and 4, against budgets of 3.
- These questions are phrased *relative to the successor* ("before Delta Lake", "before the 2024 expansion"), so lexical overlap structurally favours the successor.
- **Proposed slice:** under *explicit* historical intent, when an admitted memory has governed state-change predecessors, place its immediate predecessor (from replacement records) directly after it in the served order. Both stay subject to canonical historical admission.
- This uses only recorded lineage, needs no threshold, and does not reverse chronology: unrelated memories keep their order, and error-corrected values stay refused.
- **Expected effect, if the slice behaves as designed:** H02, H14, C02 and C07 would serve the answer within budget (rank-1 placement depends on the successor's position).
- **"Why" misses** (H12, H23, C03, C04) involve **independent** rationale memories. Lineage cannot fix them. They need a caller-declared rationale link at write time ("explains"/"motivated_by") so a served decision can co-serve its declared rationale. Do not infer it from the word "why".
- **C13 and H04 are vocabulary failures in candidate generation**, not ranking. For example "incident 208" never appears in the event text.

### G1: relevant-evidence qualification (`g1-qualification-analysis*.json`)

- I tested a scope-relative, untuned rule offline: serve only if the memory shares at least one query token that occurs in at most half of the caller's admissible scope.
  - With the runtime tokenizer it withholds 3 distractors and 2 no-answer items.
  - With possessive folding it withholds 4 distractors and 4 no-answer items, and empties one no-answer context (C21).
  - It loses **0** critical or relevant memories.
- That's safe but **insufficient**. The dominant no-answer pattern is a *wrong-subject* match on real content words: Gamma Project offset vs home offset (C23), mobile vs payments on-call (H19), relay token vs uplink relay (C22).
- **Proposed slice**, in two parts:
  1. Normalize tokenization (possessives and inflection) and apply the scope-relative discriminative-term qualification as a *necessary* condition.
  2. An **anchored coverage qualification**: the query's most discriminative in-scope term (lowest admissible-scope frequency) must be covered by a served memory; otherwise deliver no context and report `no_qualified_evidence`. That label is never abstention.
- Validate both on a **blind** set before any default change. Part 2 risks hurting paraphrase questions (H15, H21), so it must be measured on those strata specifically.
- Because tokenization changes alter every frozen lane, ship them behind a successor declaration with LongMemEval/AMB replays.

## Remaining risks

1. Cedarline is not blind, and both holdouts are small (24 questions each). The generalization finding is about reproduction of failure classes, not about magnitudes.
2. **Answer-level correctness and abstention remain unmeasured**; that needs an answering layer and an independent adjudicator.
3. The `governed-lexical` profile is write-order sensitive (from the earlier qualification). Compare it only over permutations.
4. No frozen benchmark lane was re-executed. Every runtime change discussed needs a sanctioned successor declaration first.

## Reproduce

```bash
git checkout validation/771-evaluator-cedarline-qualification
python -m unittest discover -s tests -p 'test_served_memory_*.py'
python -m unittest discover -s reference/tests -t reference -p 'test_771_served_memory_integration.py'
# Phase B (from a clean checkout of 32404f7, per docs/771-cedarline-independent-holdout-frozen-v1.md, lane ids without '.')
# Phase D: requires worktrees of 3eebb6d, 9b025f9, 9c9bf4d and the #773 validation branch at the paths in phase_d_compare.py
python reports/validation/771-evaluator-cedarline-qualification/phase_d_compare.py
python reports/validation/771-evaluator-cedarline-qualification/render_phase_bd.py
python reports/validation/771-evaluator-cedarline-qualification/g1_qualification_analysis.py [--normalize]
python reports/validation/771-evaluator-cedarline-qualification/g6_lineage_analysis.py
```
