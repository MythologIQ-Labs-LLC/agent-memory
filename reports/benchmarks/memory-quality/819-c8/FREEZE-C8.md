# #819 C8 frozen candidate: bounded rank fusion (ranking policy 3.5.0)

**Status.** C8 is implemented, tested, independently reviewed (one blocking finding, fixed) and frozen. It is not integrated or released, and it has not been independently evaluated. Development results confer no acceptance.

## Identity

| Item | Value |
|---|---|
| Frozen commit | `24d4dd2697047fc622a6087f7005775133b60209` |
| Tree / `reference/` tree | `f434e6a467938a5de1095000ac988689c2f9d086` / `c8cdb0e8836002604dd289289a09d158f5248af8` |
| Branch | `claude/eager-dirac-bftkfg-819-c8` (pushed; no PR; no workflow triggers on this branch) |
| Lineage | C6 frozen `171e67db` → C7 preregistration `415eb5c5`, runtime `d05bf2b1`, stop `bbdc71dc` → C8 preregistration `dcfe83b0` → cost `69611b3f` → review fix `f2626d0e` → freeze candidate `24d4dd26` |
| Authority | The owner authorised this successor after C7 stopped: a fresh development set, a cost budget, and I4 restated so that it gates only orderings decided by a temporal stage |
| Comparators | A `7c06468a`; C4 `bc2be631`; C6 `171e67db` (under independent evaluation) |
| Depends on | C6 (C8 is built on it). If C6 is rejected, the C7/C8 commits must be rebased onto C4 |

## Configuration under test

- **Semantic route:** `AgentMemory.open(..., semantic_retrieval="required")`. The route is optional and off by default. With it off, C8 is identical to C6 and C4.
- **Ranking policy `3.5.0`:**
  - fusion `rrf-admitted-1.0.0`: reciprocal-rank fusion, k = 60, equal weights, competition ranks;
  - lists: admitted-set BM25 > 0, shared-evidence route score, dense cosine (rounded 1e-6), over admitted memories only;
  - stage order: temporal applicability tier, exact identity, fused score, temporal order, subordinate semantic score, neutral digest;
  - explicit-current constraints and cross-fact currentness unchanged.
- **Fusion applies only when all of these hold:**
  - the provider is enabled;
  - the intent does **not** order by time (declared current, as-of or prospective, or "now"-style language, all keep 3.4.0);
  - at most 512 memories are admitted.

  Otherwise 3.4.0 ranks exactly, and the reason is recorded in `ranking_evidence.fusion.status`.
- **Selection.** `relevance_sufficient` (selection policy 2.3.0, unchanged) decides sufficiency on the 3.4.0 order. Fusion orders the selection and decides the budget cut. `ranked_prefix` returns the fused prefix.
- **Cost changes.**
  - Fusion reuses the semantic route's cosines for the same query.
  - `ranked_prefix` runs one ranking pass; `relevance_sufficient` runs two.
- **Model and dependencies** (local, no network, no paid inference):
  - `sentence-transformers/multi-qa-MiniLM-L6-cos-v1@b207367`, `onnx-mean-l2-f32/1.0.0`;
  - config digest `sha256:7447705443160d1ae7c1de49902b786bd3f578d06e7125c05dabaed52dd31aee`;
  - Python 3.13.16, onnxruntime 1.30.0, tokenizers 0.23.2, numpy 2.4.6.

## Gate (preregistered `dcfe83b0`), measured at `f2626d0e`

The runtime at `24d4dd26` differs from `f2626d0e` by one comment.

**Development set (fresh, 57 queries / 78 needed):**

| Criterion | C8 | Comparator | Bound | Result |
|---|---:|---:|---|---|
| R1. All needed evidence in the top 5 (of 51) | 27 | C4+sem 23 | ≥ 26 | met |
| R2. Needed memories in the top 5 | 43 | 36 | ≥ 42 | met |
| R3. All needed evidence in the top 10 / top 3 | 35 / 23 | 30 / 21 | ≥ | met |
| R4. Queries losing top-5 coverage | 0 | — | ≤ 2 | met |
| S1/S2. Returned sets / strict / extras / no-answer (`relevance_sufficient`) | identical / 17 / 61 / 3 | C6+sem identical | no worse | met |
| I1. Route off | identical to C6/C4 | — | identical | met |
| I4′. Declared conflicts, preferred first | 9 of 9 | C6 9 of 9 | keep all | met |
| Measured only: incidental newer-first, unspecified intent | 2 of 6 | C4 1 of 6 | — | — |

**I4′ on the reviewer's independent temporal probe** (`review-fix/`, 70 cases per configuration):

| Family | C8 | C6 |
|---|---|---|
| Declared current, both statements valid | 10/10 | 10/10 |
| "now" in the question | 10/10 | 10/10 |
| as-of | 10/10 | 10/10 |
| historical, unspecified, cross-fact | identical | identical |

**R5 and regression sets** (`ranked_prefix`, route on, against C4+sem):

| Set | Needed memories in the top 5 | recall@10 |
|---|---|---|
| C6 reviewer set (55 queries, independently authored) | 31 → **39** | 0.707 → **0.741** |
| C6 development union (78) | 49 → 51 | 0.705 → 0.731 |
| C7 development set (48) | 33 → 41 | 0.579 → 0.632 |

S1/S2 and I1 also hold on all three.

**Other invariants:**
- **I2 (governance):** forgotten, superseded, corrected, disputed, other-scope and other-tenant memories never appear among admitted or returned memories, and no refused text appears in results (tests, and the reviewer's probes).
- **I3 (determinism):** identical ranked orders across `PYTHONHASHSEED` (`determinism.txt`). Exact fused ties fall to the neutral digest, which depends on write order (deterministic for a given history).
- **I5 (cost),** preregistered probe, two runs each (`latency-f2626d0e.txt`):

  | Store | C6 p50, ms | C8 p50, ms | Result |
  |---|---|---|---|
  | 200 memories | 70.0 / 68.4 | 78.3 / 76.0 (**+8.3 / +7.6**, bound +10) | met |
  | 1,000 memories | 297.9 / 288.3 | 298.3 / 308.9 (**1.00× / 1.07×**, bound 1.15×) | met |

  RSS is flat at 213–218 MB. All repetitions across three measurement rounds are listed in DISPOSITION row 3: 5 of 6 at 200 memories are within the bound.

**Full suite at `24d4dd26`:** 2666 passed, 31 skipped, 1 expected failure (C7's falsified preregistered test 1, kept and disclosed), and 1 failed by design: `test_evaluation_only_change_keeps_runtime_baseline_equivalence`, because the protected surface changed and no successor is declared (`full-suite-24d4dd26.log`).

## What C8 is, and is not

- **It is a rank-depth improvement for `ranked_prefix` consumers** (recall@k evaluations, context assembly by rank) when the optional model is present.
- **Under the default `relevance_sufficient`, returned sets are unchanged;** only their order and the budget cut differ.
- **It does not discover new evidence.** Discovery losses remain: 16 of 45 multi-evidence memories in the C7 diagnosis. Multi-evidence completeness under default selection did not improve on the reviewer's set.

## Known limits

1. **Single-list penalty.** A memory found only by the semantic route is in one list and stays below lexical candidates.
2. **Topical, negation-blind matches.** Dense agreement is topical, not answer-bearing: near-misses and negation-blind matches can rise in rank (review note 6), and query-shaped notes rise modestly (note 7).
3. **Unspecified-intent conflicts.** Which statement comes first is decided by relevance, not time (measured, not gated).
4. **Cost.**
   - About +8 ms p50 at 200 memories (thin margin).
   - About +25 ms (+14–16%) under `relevance_sufficient` when roughly 500 memories are admitted.
   - Stores with more than 512 admitted skip fusion entirely.
5. **Failure handling.** If the route scan fails at query time in `auto` mode, recall raises (pre-existing, as in C6). The fusion fallback covers `RepresentationUnavailable` from scoring only.
6. **Similarity cache.** It is keyed by query string per retriever. That is safe through the facade (one retriever per handle, serialised); keying it by substrate is an integration hardening item.

## Integration dependencies

- **Security stack.** The C lineage predates #805 `28f257c9` → #815 `77c472e6` → #816 `e13d8c58`. Integration must rebase onto it and rerun the security replays.
- **C6 dependency.** C8 depends on C6's semantic route changes. If C6 is rejected, rebase onto C4.
- **Protected files.** A Runtime Baseline successor would have to declare these protected files:
  - `runtime/ranking_policy.py`;
  - `runtime/temporal_order_constraints.py`;
  - `runtime/runtime_composition.py`;
  - `runtime/vector_retrieval.py`;
  - `api/surface.py`.

  None is proposed. The deferred LongMemEval semantic lane would record policy 3.5.0.

## Independent evaluation requested

- **Evaluator:** fresh independent evaluation of `24d4dd26` against A, C4 and C6, with the configuration above. Use of sealed cohorts is the evaluator's decision.
- **Suggested focus:**
  - rank depth (`ranked_prefix`, recall@k) with the model on;
  - temporal ordering under time-ordered intents (C8 should equal C6);
  - near-miss and stuffing promotion;
  - cost near 500 admitted.
