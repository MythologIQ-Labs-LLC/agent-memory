# Plan: #673 post-admission route fusion (ranking policy 3.3.0, Runtime Baseline v4)

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #673. It inherits #669's movement gate (`docs/plan-669-lanes-v3.md` D4).
**owner rulings in force**: `decision-embedding-dependency` (pinned local provider, optional extra), `decision-temporal-posture`
**doctrine**: relevance != currentness; ranking != admission; similarity is evidence, never authority; benchmark score != truth
**iteration**: 1

## Purpose

Under ranking policy 3.2.0 the semantic route is ordering-subordinate. The accepted `-v3` lane measured the consequence (D2):
- the opt-in route changes no LongMemEval_S scored metric;
- the one gold item reached only through the route ranks 116 of 116 admitted.

The cause is structural. A semantic-only candidate has route-corroboration count 0, while every lexical candidate has at least 1. It also has no score in the lexical stage, so it orders after every lexical candidate.

This tranche replaces the lexical relevance stage with **reciprocal-rank fusion (RRF)** of the lexical and semantic routes. It counts the semantic route toward corroboration. The temporal stages above relevance, and the admission boundary, are not touched.

## Decisions

**F1 — Policy 3.3.0 stage list.** One stage changes and one count widens. Everything else equals 3.2.0.
- `lexical_relevance_desc:bm25_admitted_set:lexical` is replaced by `fused_relevance_desc:rrf60(lexical,semantic_vector)`.
- `route_score_desc_subordinate:semantic_vector` is removed, because the route is now fused.
- `route_corroboration_count_desc` counts every route that surfaced the candidate, now including `semantic_vector`. The exact-identity route is excluded as before.
- Stage order: `temporal_applicability_tier` → corroboration → exact identity → `route_score_desc:shared_evidence_neighbor` → **fused relevance** → `temporal_order_within_query_regime` → digest → the explicit-current unknown-tie and pairwise constraints.
- The temporal stages stay where they are: above relevance where 3.2.0 puts them there, and fused relevance never crosses a temporal applicability tier.

**F2 — The fused score.**
- `fused(c) = Σ_{r ∈ {lexical, semantic_vector}, c has a rank in r} 1 / (60 + rank_r(c))`.
- **Lexical rank:** the dense rank (1 = best; equal scores share a rank) of `lexical_relevance_score` among the primary-route candidates that carry one. BM25 statistics keep 3.2.0's scope, `admitted_set_primary_routes`, so semantic-only candidates never move a BM25 score.
- **Semantic rank:** the dense rank of similarity among candidates with a semantic hit. The minimum similarity (0.30) and candidate limit (16) are unchanged.
- `k = 60` is the standard RRF constant, fixed here before any score. It is never tuned against a lane.
- Evidence records per candidate: `fused_relevance_score`, `fused_ranks` (`{route: rank}`) and `fusion: "rrf60"`.
- `lexical_relevance_score` and `semantic_similarity` stay recorded unchanged.

**F3 — Exact equality when the route is off.** This is the shipped default.
- With no semantic hit, each candidate's fused score is `1/(60 + dense_rank_lex)`. That is a strictly decreasing function of the BM25 score, and equal BM25 scores give equal fused scores. The corroboration count is unchanged.
- So 3.3.0 orders every candidate set exactly as 3.2.0, ties included.
- Test: the 3.2.0 equivalence oracle over the same query set as `test_semantic_route_policy_320.py`. Assert equal order and equal `ordered_before_next_by` stage names, mapped `lexical_relevance_desc:*` → `fused_relevance_desc:*`.
- Report re-run: the route-off half of the #669 ordering-difference report must be unchanged.

**F4 — Doctrine guards.** Each is a test.
- No admission change. The admitted set is identical with and without fusion.
- No candidate crosses a `temporal_applicability_tier` because of fusion.
- With the route on, the #584 M1–M15 expectations and every #580 required unit keep their status. This is rerun through the ordering-difference report against the real pinned provider. Any change blocks the tranche; it is not re-pinned.
- Similarity enters only as a rank. It never becomes an applicability, currentness or authority input.

**F5 — Identity and succession.**
- `identity.ranking.active_policy_version` changes from 3.2.0 to 3.3.0.
- The re-pins follow the #669 list: the post-admission ranking policy test, the temporal-order tests, the `stop-set` stage names and the `VERSIONED_RANKING_TRANSITIONS` entry if the #584 machinery requires one.
- Runtime Baseline **v4** is declared through docs/67 Step A (`reports/runtime/baseline-v4-declaration.json`). The acceptance evidence is lanes `-v4` and the gauntlet probe.
- `pyproject.toml` is unchanged; the extra already exists.

**F6 — Default posture is unchanged.** `semantic_retrieval` stays `off` by default.
- Turning the route on by default would make the optional extra a de-facto requirement. That contradicts `decision-embedding-dependency`, so it is out of scope.
- An `auto` default, meaning "use the route when the extra and the model are installed", is an owner question. It is recorded under Open Questions and does not block this plan.

**F7 — Pre-registered movement gate.** It is frozen in the `-v4` lane file before any score.
- The LongMemEval_S `agent_memory_semantic` row is the same D2 identity as `-v3`, now executing 3.3.0. It must show a **strict increase** over the `-v4` control (route off) on:
  - turn `recall_all@50`;
  - session `recall_all@5`;
  - both measured on the same 419 scored questions.
- **Reported, not gated:**
  - `ndcg_any@5/@10` on both planes;
  - the knowledge-update slice;
  - `latest_gold_ranked_first`;
  - per-question up and down counts for every `recall_all@k`.
- A decrease on any of these is recorded as a finding and does not block acceptance.
- If the gate fails, 3.3.0 is still publishable, because the control holds D1 equality. #673's gate then stays open with the evidence, and nothing is re-tuned after the score.
- **D1 analogue for publication:** every row of the `-v4` lanes run with the route off equals its `-v3` row exactly.

**F8 — MESA replay.**
- The frozen formal MESA runner is replayed through a `mesa-formal-v2` successor freeze, in which only the `agent_memory` block changes. It runs with the route off (the shipped default) and is expected to equal `-v1`.
- A second freeze identity runs with the route `required`, as a diagnostic. M4 is read through `win_basis`: a relevance gain is never reported as currentness.

## Implementation steps (after gate PASS)

1. `ranking_policy.py`: add a `fused_routes` field and the fused stage, the evidence fields, and the dense-rank helpers. Keep the empty-`fused_routes` identity byte-identical to the base policy.
2. `temporal_order_constraints.py`: set `POLICY_VERSION = "3.3.0"`, and add the fused stage name to the stop-set.
3. `runtime_composition.py`: `MULTI_ROUTE_RANKING_POLICY` gets `fused_routes=(LEXICAL_ROUTE, SEMANTIC_VECTOR_ROUTE)` and no subordinate routes.
4. Tests:
   - `test_route_fusion_policy_330.py` covering F3, F4, F2 arithmetic and tie handling;
   - the re-pins listed in F5;
   - the ordering-difference report regenerated.
5. The v4 declaration, via `scripts/declare_runtime_baseline_changes.py`, with the checker showing TRANSITION.
6. Ledger entry. The PR merges with a merge commit.
7. A separate plan (`docs/plan-673-lanes-v4.md`, with its own gate) freezes the `-v4` lanes from `-v3` under the F7 gate. Then dispatch, acceptance, and docs/67 Step B1/B2 for v4.

## Boundaries

- **Non-goals:**
  - a learned reranker (`space-reranker-model`; a later, separately versioned stage);
  - default-on semantic retrieval (F6);
  - typed-graph fusion. #688 has no executed scored route yet.
- **Exclusions:**
  - no admission change;
  - no temporal-stage change;
  - no BM25 parameter change;
  - no change to the semantic minimum similarity or candidate limit;
  - no benchmark-specific behaviour;
  - no tuning of `k` after any score.

## Open Questions

- (owner, non-blocking) Should the facade default become `semantic_retrieval="auto"` once 3.3.0 is published, so the route engages wherever the extra is installed? This would need its own lane generation and baseline transition.
