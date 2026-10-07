# Plan: #644 T-controller — shadow recall control on the facade (no retrieval or ranking change)

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #644, first Jev-Mem tranche (`docs/plan-672-tranche-5-harvests.md` LD5). This is #644's own "Phase 3 — shadow adaptive retrieval".
**contracts**: `reference/fixtures/runtime/system-one-controller-contract-v1.json` (frozen); `reference/fixtures/harvest-closeout-final-v2.json` (published, never edited)
**doctrine**: routing != recall admission; controller output != truth; stop recommendation != actual stop reason; stopping because sufficient != stopping because budget exhausted
**iteration**: 2

Gate history:
- **Attempt 1, VETO.** The controlled planner's candidate generation differs from the default planner's in three ways:
  - lexical-anchor shared-evidence expansion;
  - a vector limit of 24 against the facade's 16;
  - no vector domain prefilter.

  That changes ranking inputs, so "ranking unchanged" was false. Lexical truncation can also drop the current fact while the stop reads as "sufficient". The C10 guards were vacuous on the existing corpora. Further faults: missing contract fields, a missing public-contract bump, and an edit to a published fixture.

  The prototypes are in `scratchpad/gate644/`.

This iteration removes the controlled execution path from the facade. The controller runs in **shadow**: it plans, the default planner executes exactly as today, and the facade reports the controller's proposal beside what actually ran.

## Decisions

**S1 — The seam.**
- `AgentMemory.open(..., recall_control="off" | "shadow")`, default `"off"`.
- **Retrieval is identical in both modes:** `candidates`, `admitted`, `returned`, `admissions` and `ranking_evidence` are the same.
  - Tested byte for byte over the facade test corpus.
  - Also tested over new cases built to expose the attempt-1 differences: more than 32 lexical hits, shared evidence reachable from lexical anchors, more than 16 vector-eligible facts, and cross-domain facts.
- `"shadow"` only adds the `recall_control` block (S3).
- Shadow runs inside the same governed read and audit path (`run_governed_read`, `runtime/sqlite_composition.py`). It writes nothing to the audit beyond what the default recall writes.

**S2 — The shadow controller.**
- `DeterministicRecallController.plan()` is called once per recall with:
  - the query;
  - the logical memory references;
  - the routes the default planner *actually* has available: lexical, exact identity, shared evidence, and `semantic_vector` when the semantic route is enabled.
- The plan never reaches candidate generation.
- Its budgets are compared with the default planner's actual per-route candidate counts, and the result is a **counterfactual delta** per route: `proposed_limit`, `actual_count`, and `would_truncate: actual_count > proposed_limit`.
- No counterfactual ranking is computed. The delta states what the budget *would* bound, never what the result *would* be.

**S3 — The telemetry block (JH-14).** It maps onto the frozen contract's request, response and usage fields:
- **Request:**
  - `operation: "retrieval_planning"`;
  - `available_capabilities` (the S2 route list);
  - `budget: {maximum_controller_decisions: 1, deadline_ms: null}`;
  - `policy_context: {tenant_scope_ref, recall_policy_ref, controller_contract_version: "1.0.0"}`.
- **Response:**
  - `controller_identity` (`backend_ref`, `backend_version`, `model_or_policy_ref`);
  - `decision_status` (`complete`, or `invalid_response` and `unavailable` from S4);
  - `evidence.route_budgets` (the plan);
  - `evidence.stop_recommendation: "abstain"` (the deterministic controller makes no sufficiency judgement);
  - `authority_effect: "none"`.
- **Usage:** `controller_decisions_used` (counted), `cache_hits: 0`, `elapsed_ms`, `fallback_events`.
- **Actual stop record:**
  - `actual_stop_reason: "frontier_exhausted"` (class `search_space`), because the default planner runs every available route without a budget;
  - `controller_recommendation: "abstain"`;
  - `budget_state`.
  - A quality class is never reported, because nothing decided on quality.
- **Shadow delta:** the S2 per-route counterfactual.
- `elapsed_ms` is non-deterministic and excluded from every digest and lane metric.

**S4 — Controller failure.**
- An exception, or a plan that fails `RecallControlPlan` validation, yields `decision_status: "unavailable"` or `"invalid_response"`, `fallback_events: ["controller_failure_no_effect"]`, and the same recall output.
- Shadow has no authority to lose, so it needs no fallback planner.
- Tested at planner level through an injected failing controller. The facade does not accept controller injection.

**S5 — Public contract 1.5.0.**
- The result envelope forbids unknown fields (`schemas/api-result-envelope.schema.json`, and the protected copy under `reference/agentmem_ref/_schemas/`).
- Adding the optional `recall_control` field is a minor contract bump, following the precedent of 1.3.0 and 1.4.0.
- Files:
  - both schema copies;
  - `api/contract.py` (`CONTRACT_VERSION` 1.4.0 → 1.5.0);
  - docs/44: status, `open()` and recall sections.
- With `"off"`, `recall_control` is absent and every other field is unchanged.

**S6 — A harness bug fixed in passing.**
- The harness planner's vector search runs without the domain-eligibility prefilter (`runtime/recall_control.py:607-612`). This contradicts docs/44, which says the prefilter is "not optional per request".
- Fix: pass `eligible=` as the default planner does (`runtime_composition.py:214`).
- This is harness-only behaviour, so the facade is unaffected. It is a protected-file change, so it is declared in S7. Tested with a cross-domain vector case.

**S7 — Succession: Runtime Baseline v4, docs/67 Step A.**
- Declaration `reports/runtime/baseline-v4-declaration.json`, and the register's `declared_successor` (A.3).
- `declared_changes` comes from the script.
- The identity delta is `identity.public_contract_version` 1.4.0 → 1.5.0. The ranking policy stays 3.2.0.
- `pyproject_change: null`.
- `acceptance_evidence_required` names, now:
  - lanes `amb-precisionmembench-retrieval-v4` and `longmemeval-s-retrieval-parity-v4`;
  - the public Gauntlet probe.
- The declaration and the v4 record (at B1) correct the stale `native_qualified` capability claims the CONTRIBUTOR_ARCHITECTURE rule requires. `typed_relations_graph_traversal` and the controller planner are recorded as harness-only.
- If #671 is ruled during the transition, it amends this declaration (A.6).
- At B1 the successor adapter's `PUBLIC_CONTRACT_VERSION` is 1.5.0.

**S8 — Closeout fixture v3.** The published v2 is never edited (CONTRIBUTOR_ARCHITECTURE §10). `reference/fixtures/harvest-closeout-final-v3.json` supersedes v2 and changes only these rows. Each carries an issue, an order and the lane gate.
- **`jh-14-telemetry`:** stays `tranche`, with T-controller evidence attached (tests). It becomes `shipped` only after the `-v4` lanes are accepted, because the row's lane gate requires them.
- **`jh-06-call-deadline-budget`:** stays `tranche` and moves to T-controller-2. Shadow enforces no budget, so there is nothing to ship.
- **`jh-04-route-needs`:** moves to T-controller-2. The contract types route needs as probabilities, and the deterministic controller has no calibrated estimate.
- **`jh-09-bounded-traversal`:** moves to T-controller-2, with node, edge and depth bounds.
- **`codegenome-graph-propagation`:** moves to issue #688. Facade typed-graph hits would change the corroboration inputs to ranking.
- **JH-15 ablations:** `controller_off` against `shadow` is the only pair this tranche can measure. The rest move to T-controller-2.

**S9 — Evidence: a separate gated lanes plan (`-v4`).**
- **D1:** the default (`"off"`) equals `-v3` exactly.
- **A `shadow` row per lane:** its scored metrics must equal the control's exactly (the S1 invariant at lane scale). Its route deltas are reported per question, and are evidence for T-controller-2's budget design.

## Implementation steps (after gate PASS)

1. `api/surface.py`: the `recall_control` parameter, the shadow invocation inside the governed read, the telemetry block and the posture text.
2. `runtime/recall_control.py`: the S6 prefilter fix, plus a pure helper that builds the S3 block from a plan and the actual route counts.
3. S5 contract and schema files, and docs/44.
4. Tests:
   - `test_facade_recall_control.py`: S1 equality over the adversarial cases, S3 contract conformance against the frozen fixture, S4 failure, the S6 prefilter;
   - updates to `test_recall_control.py` (the S6 prefilter case);
   - contract-version re-pins.
5. `harvest-closeout-final-v3.json` (S8), with its test.
6. The v4 declaration (S7), with the checker showing TRANSITION. Then a ledger entry and a merge commit.

## Boundaries

- **Non-goals:**
  - any change to candidate generation, admission or ranking on the facade;
  - an enforced budget (JH-06) or adaptive stopping (JH-07), both T-controller-2;
  - the typed-graph route;
  - learned or hosted controllers;
  - consumer packaging (#691).
- **Exclusions:**
  - no default behaviour change;
  - no benchmark-specific behaviour;
  - no non-deterministic field in any digest.

## Open Questions

None blocking.
