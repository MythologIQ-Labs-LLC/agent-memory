# #644 — Typed post-admission evidence sufficiency, v1 candidate

**Status:** implementation committed on unopened, non-main branch; 17 focused local tests passed on byte-identical source; integration/full-runtime replay **not yet qualified**. **Change class:** protected runtime-bearing candidate. **Baseline:** current immutable v6 remains controlling; prepare a fully pinned v7 successor declaration and its lane/gauntlet evidence before merging. No register, frozen benchmark or runtime baseline was edited. **Authority:** none.

## Problem this slice fixes

The existing `ControlledRecallResult.evidence_sufficiency_met` is `len(ranked_admitted) >= plan.evidence_sufficiency_target`. This is only an **admitted result-count threshold**. It cannot establish task-relevant support, resolve contradictions, distinguish resource saturation from complete search, or authorize stopping. It must not become a general `quality_sufficient` predicate by accident. In parallel, #644's facade `shadow_control_report` abstains from sufficiency, by design.

## Implemented, executable seam

`reference/agentmem_ref/runtime/evidence_sufficiency.py` provides an isolated, versioned, deterministic observer:

```text
governed admitted reference set
+ caller/host-declared typed needs (identity and required admitted support count)
+ admitted-only per-fact support mapping, with typed-vs-estimate provenance label
+ admitted-only contradiction pairs
+ executed route work and enforced candidate ceilings
    -> mechanical coverage counts and missing needs
    -> contradiction and route-budget/unfinished-frontier diagnostics
    -> review-only continuation proposal
    -> no admission, no mutation, no stopping, no truth certificate
```

`ControlledRecallResult.observe_evidence_sufficiency(...)` binds the observer to the actual `recall.admitted` set, the `RecallControlPlan`'s executed route budgets and actual `route_candidate_counts`. It is **opt-in inspection only** and returns a typed `SufficiencyReport`; it does not modify `recall()`, the default facade, any candidate, refusal, ranking or lifecycle state. The count threshold is still available separately as `count_target_met`, never as answer proof.

The observer counts `CoverageObservation(origin='runtime_typed_observation')` toward *mechanical* coverage and ignores `controller_estimate` for satisfying a need. The origin value in a supplied object is **not authenticated by this helper**. A production host must bind that label to persisted, scope-permitted typed evidence rather than trusting a controller to self-label. Consequently even a mechanical coverage hit has `answer_quality_verified=false`, `can_admit=false`, `can_mutate=false` and `authority_effect='none'`. `review_stop` is a non-executable proposal, not an actual stop reason. Missing needs, contradictions, route caps and incomplete routes always produce `continue_if_permitted` where applicable; no restart/retrieval budget is implicitly extended.

## Deterministic safety controls

- Identity references and need keys are typed, unique where required, bounded, control-character-free; coverage and contradiction references must all belong to the governed admitted set, never pre-admission candidates.
- Controller estimates cannot be laundered into mechanical typed support; repeating a claim for the same fact cannot satisfy a support multiplicity target.
- Contradictions stay separate from missing needs. Two admitted conflicting statements can prevent a proposed quality stop even when mechanical need coverage is present.
- `returned_count == candidate_limit` is **conservatively** reported as resource-bound, never proof that the frontier was fully searched; disabled routes are not capped.
- Unexecuted planned routes are explicitly distinguishable from executed but empty routes.
- Count adequacy, typed coverage, contradiction, budget exhaustion, actual authority and task answer quality never collapse to one scalar.
- Output order is stable independent of admission, route, need, and support observation ordering; no benchmark phrases or gold labels inform runtime logic.

## Evidence and next gates

**Locally executed:** `python -m unittest discover -s /mnt/data/am644/reference/tests -p 'test_evidence_sufficiency.py' -v`, 17/17 passing. The source committed to GitHub has byte-exact Git blob hashes matching locally tested source (`evidence_sufficiency.py` `2011c45d36e0291ec352a1d1a559f1758852a003`; unit tests `1c0decdd837ab7189525854f482d1e259382e971`). The added `reference/tests/test_recall_control.py` integration assertion has **not yet run**, because the connected desktop checkout is offline.

1. Locally checkout the quiet branch; execute `python -m unittest discover -s reference/tests -t reference -p 'test_evidence_sufficiency.py' -v` and `-p 'test_recall_control.py'`, then the full reference suite and baseline checker. No GitHub Actions during iterative development.
2. Independently challenge forged provenance labels, structural contradictions, capped-route continuation, foreign scoped candidate injection, empty typed needs, duplicate references and shuffled enumeration.
3. Build authentic runtime-generated typed-support provenance instead of accepting an estimator-supplied origin label as independent truth. That is the prerequisite for any externally usable `review_stop` consumer.
4. Follow `docs/67-runtime-baseline-succession.md`: declare only the actual protected file blobs and identity deltas in the v7 candidate, run the exact v6 replay and cross-benchmark memory/governance/latency gates, and publish only after explicit acceptance. Until then this is an **unmerged runtime candidate**, not the published v6 behavior.
5. A later separate tranche may feed this diagnostic into cost-aware adaptive route selection or consumer packaging. Requiring actual stop decisions must be a later, independently qualified policy evolution, never an implicit consequence of observing `mechanical_coverage_met`.

### Non-goals

No changes to `#732` frozen R6, currentness interpretation, cross-fact admission, ranking 3.4.0, benchmark/scorer definitions, trust-state #757, P.A.I., durable canonical state or public `AgentMemory` result contract. No new GitHub Actions workflow.
