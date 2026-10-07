# Plan: #644 T-controller-2 — governed adaptive recall control

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**status**: WIP / HOLD until Runtime Baseline v5 is fully published (docs/67 B1+B2)
**owning issue**: #644
**predecessor**: docs/plan-644-t-controller.md
**frozen contract**: reference/fixtures/runtime/system-one-controller-contract-v1.json
**runtime base**: a9fa96211f65f07a3d1b2545ba6e9d5782db69fb

## Purpose

Implement the second native Jev-Mem controller tranche without weakening the
authority boundary established by the first shadow-controller tranche.

T-controller-2 owns the mechanisms still recorded as tranche work:

- JH-02 — bounded candidate-search comparison;
- JH-05 — explicit total-budget allocation;
- JH-07 — evidence-sufficiency / adaptive stopping;
- JH-12 — typed probabilities/evidence on controller outputs;
- JH-13 — version/scope-bound decision cache;
- JH-15 — routing, budgeting, stopping and combined-controller ablations.

It does not own ranking (#673), typed-relation activation (#688), consumer
packaging (#691), lifecycle mutation, truth, currentness authority or recall
admission.

## Sequencing hold

The branch was opened from the exact merge of the frozen #671 MESA v2 protocol.

The original hold was the MESA v2 replay required by
`docs/plan-671-evidence-v5.md` E7 step 3. That hold is satisfied:

- PR #727 froze the MESA v2 protocol;
- PR #728 merged the replay with M4 `new_fact = 1.000` and 250/250 wins
  attributed to `currentness_mechanism`.

A stricter docs/67 hold remains. Runtime Baseline v5 is already the declared
successor for #671. T-controller-2 changes the protected
`reference/agentmem_ref/runtime/recall_control.py` blob beyond that declaration,
so it cannot be merged under the v5 transition.

PR #731's AGMI run `37683798859` proved this fail-closed boundary on its first
2A head by reporting a declared-blob mismatch for `recall_control.py`.

Therefore:

1. development, focused tests, and broad CI may continue on this branch;
2. no T-controller-2 runtime commit may merge before #671 completes its E7
   acceptance and Runtime Baseline v5 docs/67 B1+B2 publication;
3. after v5 is published, T-controller-2 must declare a new Runtime Baseline
   successor before merge;
4. the v5 declaration must not be edited or widened to absorb this tranche.

This is a baseline-sequencing hold, not a controller-quality failure.

## Design

### T2-1 — Separate estimator mechanics from enforcement

The first implementation slice adds deterministic, provider-neutral primitives:

- RecallOuterBudget;
- RecallRouteNeed;
- EvidenceAssessment;
- AdaptiveControlDecision;
- ControllerDecisionCache;
- deterministic route-need estimation;
- deterministic largest-remainder route-budget allocation;
- four-way evidence assessment;
- explicit ablation profiles.

These primitives are runtime code, not benchmark helpers.

The deterministic baseline may emit only boundary-valued probabilities
(0.0 or 1.0) until calibration evidence exists. It must not manufacture
pseudo-probabilities that merely look scientific.

### T2-2 — Outer budget

One request budget owns controller work:

- maximum_controller_decisions;
- maximum_candidates;
- optional deadline_ms;
- optional maximum_nodes;
- optional maximum_edges;
- optional maximum_depth.

Every value is non-negative and finite where applicable.

Allocation is bounded twice:

1. the outer request budget;
2. host route caps.

A controller cannot create capacity the host did not expose.

### T2-3 — Route needs

Route needs are evidence over host-declared available routes.

Deterministic baseline:

- exact identity need = 1 only when logical refs exist;
- lexical need = 1 only when content terms exist;
- semantic need = 1 only when content terms exist and semantic is available;
- typed graph need = 1 only when identity seeds exist and the route is available;
- shared-evidence need = 1 only when content or identity seeds exist and the route is available;
- otherwise 0.

These are deterministic boundary values, not learned calibration.

### T2-4 — Allocation

Active routes are those with need > 0.

The allocator:

1. clamps total requested candidate work to the outer maximum;
2. gives each active route a minimum allocation of one when capacity permits;
3. distributes remaining capacity by largest remainder over need weights;
4. clamps each route to the host cap;
5. redistributes unused capacity deterministically while eligible routes remain.

Tie order is an explicit stable route order, never dict iteration order.

No allocation changes recall admission or ranking.

### T2-5 — Evidence assessment

The controller preserves the frozen four-way evidence shape:

- evidence_sufficient;
- continue_useful;
- missing_evidence;
- contradiction.

The deterministic baseline uses inspectable conditions and emits only 0.0/1.0.

Evidence can be sufficient only from caller-visible candidate evidence.

Resource exhaustion never implies sufficiency.

Contradiction never becomes truth authority.

### T2-6 — Stop recommendation

Recommendations remain separate from actual stop reasons.

Possible recommendations are exactly the frozen contract vocabulary:

- evidence_sufficient;
- further_retrieval_unhelpful;
- continue_retrieval;
- budget_exhausted;
- frontier_exhausted;
- controller_unavailable;
- abstain.

The host records the actual stop separately.

### T2-7 — Decision cache

The cache is process-local derived controller evidence.

Its key binds:

- operation;
- canonical request state;
- controller contract version;
- backend identity;
- model/policy identity;
- host policy version;
- tenant/isolation namespace.

Cache hits carry no authority and do not bypass ordinary validation.

No cache is persisted in canonical memory.

### T2-8 — Ablations

The runtime exposes internal ablation identities:

- controller_off;
- adaptive_routing_only;
- adaptive_budgeting_only;
- adaptive_stopping_only;
- combined_controller.

Ablation selection must not alter governance/admission rules.

### T2-9 — Enforcement is a second slice

This branch first proves estimator/allocation/sufficiency/cache mechanics.

Facade enforcement is not added until:

- the primitives pass CI;
- a gated enforcement plan fixes progressive-route execution semantics;
- candidate evidence used for stopping is proven domain-safe;
- one canonical admission pass is preserved;
- the public-contract version decision is explicit.

This prevents “adaptive stopping” from accidentally becoming repeated admission,
an audit side effect, or a cross-domain side channel.

## Acceptance for slice 2A

Tests prove:

1. route needs cannot name unavailable routes;
2. allocation is deterministic across input order;
3. total allocations never exceed the outer budget;
4. host caps cannot be exceeded;
5. boundary probabilities reject NaN/out-of-range values;
6. resource exhaustion is not evidence sufficiency;
7. contradiction is represented independently;
8. cache keys separate tenant, policy, backend and contract identity;
9. cache hits do not mutate canonical memory;
10. every mandatory ablation identity is represented;
11. existing off/shadow facade behavior is unchanged;
12. System-One authority invariants remain true.

## Non-goals

- default behavior change;
- facade adaptive enforcement in slice 2A;
- learned/hosted controller requirement;
- ranking/fusion changes;
- typed-graph activation;
- benchmark-specific cue lists;
- recency as currentness;
- lifecycle mutation;
- universal controller quality score;
- merging before mesa-formal-v2 is executed.
