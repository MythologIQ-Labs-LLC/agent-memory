# #644 — Typed post-admission evidence sufficiency, v1 candidate

**Status:** implementation staged on unopened, non-main branch; **18/18 focused unit tests passed locally on the current evidence-sufficiency module's exact Git blob**, while the extended adapter/controller integration tests remain **unexecuted**. Full-runtime replay **not yet qualified**. **Change class:** protected runtime-bearing candidate. **Baseline:** current immutable v6 remains controlling; prepare a fully pinned v7 successor declaration and its lane/gauntlet evidence before merging. No register, frozen benchmark or runtime baseline was edited. **Authority:** none.

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

## New implementation: adapter-backed persisted typed support

The earlier `ControlledRecallResult.observe_evidence_sufficiency(...)` accepts caller-provided coverage observations for diagnostics. Even when such an observation labels itself `runtime_typed_observation`, it is **not a verified source**. Accordingly, this manual API now **always returns `continuation_proposal=continue_if_permitted`**, even if its mechanical coverage field is true. Caller-supplied origin labels cannot create a stopping recommendation.

The new `ControlledRecallPlanner.observe_persisted_typed_coverage(result, context, needs=...)` is a separate executable method. The caller declares only the **canonical typed-slot needs** and minimum admitted fact counts. The caller cannot supply supporting fact IDs or assert a support origin. For each candidate already in the controlled recall's admitted set:

1. `GovernedMemoryAdapter.current_governed_typed_slot(...)` rechecks current tenant, scope/project/task/shared-space eligibility, disputes, event invalidity, transaction expiry, source tombstones and deletion. If the recheck refuses access, the fact is omitted **before** its semantics are read.
2. The adapter reads the fact's already-persisted `write_semantics` under its independent visibility gate.
3. Only a structurally validated, exact-slot, `basis=caller_declared` typed proposition with no ineligibility reasons or asserted hedge/quote/attribution/conditional/negation/sarcasm flags contributes **mechanical** support. An extractor result, inferred English parse or controller estimate contributes zero.
4. The deterministic report includes deduplicated `need_support_counts`, **exact governed `need_support_refs`**, missing needs, route-cap diagnostics and the separate count threshold. Non-typed facts still contribute to the current-admitted count.
5. Neither path changes the original recall candidate set, ranking, refusal, audit log, lifecycle state or true stopping behavior. A `review_stop` from adapter-backed mechanical coverage is **not executable**, and none of the report fields verifies factual truth or independent source credibility.

**Limits that remain explicit:** the result's admitted-reference list is mutable in the internal reference layer, observations are not an atomic historical snapshot, and caller-declared propositions can be factually false. The adapter recheck protects permission even when a candidate reference is injected into a result, but it does not authenticate the original query membership, establish source independence, infer temporal supersession, or automatically classify competing values as contradictions. These limitations block real autonomous stopping or production authority until addressed and independently tested. The helper conservatively declines historical/as-of supporting facts rather than reinterpreting them as current.

## Deterministic safety controls

- Identity references and need keys are typed, unique where required, bounded, control-character-free; coverage and contradiction references must all belong to the governed admitted set, never pre-admission candidates.
- Controller estimates cannot be laundered into mechanical typed support; repeating a claim for the same fact cannot satisfy a support multiplicity target.
- Contradictions stay separate from missing needs. Two admitted conflicting statements can prevent a proposed quality stop even when mechanical need coverage is present.
- `returned_count == candidate_limit` is **conservatively** reported as resource-bound, never proof that the frontier was fully searched; disabled routes are not capped.
- Unexecuted planned routes are explicitly distinguishable from executed but empty routes.
- Count adequacy, typed coverage, contradiction, budget exhaustion, actual authority and task answer quality never collapse to one scalar.
- The immutable report also refuses direct construction with forged answer-quality, admission, mutation, authority or execution proposals. Output order is stable independent of admission, route, need, and support observation ordering; no benchmark phrases or gold labels inform runtime logic.

## Candidate Runtime Baseline v7 (not active)

`reports/runtime/baseline-v7-declaration.json` now preregisters exactly **three protected blob changes**, `runtime/adapter.py`, `runtime/evidence_sufficiency.py`, and `runtime/recall_control.py`, against the immutable published v6, with no public contract or ranking identity delta. It names the existing public gauntlet and AMB/LongMemEval v6 replay as non-regression gates plus a new noninterference/negative-control replay requirement. The declaration is only a *candidate file*: `reports/runtime/baseline-register.json` still has `declared_successor=null`; no v7 baseline exists, and this candidate must not be merged without completing `docs/67` transition/publication and all evidence.

## Evidence and next gates

**Executed locally on exact current module bytes:** `python -m unittest discover -s /mnt/data/am644/reference/tests -p 'test_evidence_sufficiency.py' -v` passed **18/18**, and `compileall` passed. The tested module Git blob is `8d556f6a5a76fb68d89879f50a070e90188c5032`; the focused test blob is `3955e1acff1d7562fc991451d8e6d64063bf2b15`. The adapter-backed read method and changes to `recall_control.py`, plus extended `test_recall_control.py` integration cases, **have not been executed against the full repository** because the connected desktop is offline. Neither a standalone suite nor source hash validation qualifies v7 for merge.


1. Locally checkout the quiet branch; execute `python -m unittest discover -s reference/tests -t reference -p 'test_evidence_sufficiency.py' -v` and `-p 'test_recall_control.py'`, then the full reference suite and baseline checker. No GitHub Actions during iterative development.
2. Independently challenge forged provenance labels, structural contradictions, capped-route continuation, foreign scoped candidate injection, empty typed needs, duplicate references and shuffled enumeration.
3. Expand adapter-backed typed-support provenance into an immutable, revision-bound governed observation before using it for autonomous stopping. The current persisted caller-declared slot is genuine stored evidence but is not a verified factual statement, independent source, or authenticated query-membership receipt.
4. Follow `docs/67-runtime-baseline-succession.md`: verify the three exact protected blob declarations and unchanged identity table in the v7 candidate, run the exact v6 replay and cross-benchmark memory/governance/latency gates, and publish only after explicit acceptance. Until then this is an **unmerged runtime candidate**, not the published v6 behavior.
5. A later separate tranche may feed this diagnostic into cost-aware adaptive route selection or consumer packaging. Requiring actual stop decisions must be a later, independently qualified policy evolution, never an implicit consequence of observing `mechanical_coverage_met`.

### Non-goals

No changes to `#732` frozen R6, currentness interpretation, cross-fact admission, ranking 3.4.0, benchmark/scorer definitions, trust-state #757, P.A.I., durable canonical state or public `AgentMemory` result contract. No new GitHub Actions workflow.
