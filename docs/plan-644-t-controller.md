# Plan: #644 T-controller — a facade-level recall-control seam (no ranking change)

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #644, first Jev-Mem tranche (`docs/plan-672-tranche-5-harvests.md` LD5, T-controller)
**contracts**: `reference/fixtures/runtime/system-one-controller-contract-v1.json` (frozen); `reference/fixtures/harvest-closeout-final-v2.json` rows `jh-06`, `jh-14`, `jh-04`, `jh-09`, `codegenome-graph-propagation`
**doctrine**: routing != recall admission; ranking != recall admission; controller output != truth; stopping because sufficient != stopping because budget exhausted; recency != currentness
**iteration**: 1

## Purpose

`ControlledRecallPlanner` (`runtime/recall_control.py`) exists but is harness-only. Its controller output, route budgets, route counts and stop reason never reach a facade caller, and `controller_calls` is a constant 1.

This tranche makes controlled recall reachable through `AgentMemory` as an opt-in. It changes no ranking semantics and no default behaviour. It also implements the frozen controller contract's host-side obligations:
- an outer budget;
- distinct actual-stop classes;
- usage telemetry.

The harness planner sorts with `CONTROLLED_RECALL_RANKING_POLICY`, which orders `semantic_vector` before `lexical`. Exposing that on the facade would let similarity decide over relevance. The #673 gate measured that pattern regressing the frozen #580/#584 contracts. So the facade path ranks with the facade's own policy (C2).

## Decisions

**C1 — The seam.**
- `AgentMemory.open(..., recall_control="off" | "deterministic")`, default `"off"`.
- `"off"` is the current path, byte for byte. No controlled-planner code runs.
- `"deterministic"` routes every `recall` through `ControlledRecallPlanner` with `DeterministicRecallController`.
- Custom controller injection is not exposed on the facade in this tranche (see C8).

**C2 — Ranking unchanged.**
- `ControlledRecallPlanner` gains a `ranking_policy` constructor argument. It defaults to `CONTROLLED_RECALL_RANKING_POLICY`, so the harness is unchanged.
- The facade passes `MULTI_ROUTE_RANKING_POLICY` (3.2.0), the same object the default path uses.
- The facade's controlled path executes exactly the facade's routes: lexical, exact identity, shared evidence, and `semantic_vector` (subordinate) when `semantic_retrieval` enables it.
- The typed-graph route is **not** reachable in this tranche (C9).
- Admission is the same governed `admit_preselected_candidates` call. The controller's budgets bound candidate generation only.

**C3 — Outer budget (JH-06).** This is the host-enforced budget the contract requires.
- `recall_control_budget = {"maximum_controller_decisions": int >= 1, "deadline_ms": int >= 1 | None}`.
- Default: `{1, None}`. With no deadline, results stay deterministic, which benchmark lanes need.
- **Deadline:** checked between route executions. When it is exceeded, the remaining planned routes are skipped. The candidates already gathered still go through admission, and the actual stop reason is `max_latency`.
- **Decisions:** the deterministic controller makes one decision. `controller_decisions_used` is counted, not constant. A plan requesting more than the budget allows is refused as `max_controller_decisions`.

**C4 — Actual stop record.** It is separate from any controller recommendation and uses the contract's classes:
- **quality:** `evidence_sufficient` when the ranked admitted count reaches the plan's `evidence_sufficiency_target` and every planned route ran;
- **search_space:**
  - `frontier_exhausted`: all planned routes ran and the target was not met;
  - `no_evidence`: zero candidates;
- **resource:** `max_latency`, or `max_controller_decisions`;
- **controller_failure:** `controller_unavailable` or `invalid_controller_response`.
  - These fall back to the default facade planner. Its authority is no greater, and the event is recorded in `fallback_events`.

Invariant (tested): a resource stop is never reported as `evidence_sufficient`, even when the target count was reached.

**C5 — Telemetry (JH-14).** `recall()` returns a `recall_control` block only when control is on. Its fields:
- controller identity (`backend_ref`, `backend_version`, `model_or_policy_ref`);
- the plan (`RecallControlPlan.to_dict()`);
- `routes_executed` and `route_candidate_counts`;
- usage: `controller_decisions_used`, `cache_hits` (0), `elapsed_ms`, `fallback_events`;
- the actual stop record: reason, class, `controller_recommendation`, `budget_state`;
- `authority_effect: "none"`.

`elapsed_ms` is non-deterministic and is never part of any digest or lane metric.

**C6 — JH-09 bounds.** Per-route `candidate_limit` and `anchor_limit` are the bounds this tranche exposes, and they are recorded. Node, edge and depth bounds belong to graph traversal (C9).

**C7 — Deferred, with reasons** (the #672 closeout rows are updated to say so):
- **JH-04 route needs:** the contract types them as probabilities. The deterministic controller has no calibrated estimate, and emitting rule-derived 0/1 values as probabilities would violate the contract's typed-probability rule. Moved to T-controller-2 with JH-12.
- **JH-15 ablations:** only `controller_off` versus `combined_controller` is meaningful for a single deterministic controller. The remaining contract ablations need separable adaptive components (T-controller-2).

**C8 — JH-11 backend neutrality.**
- The `RecallController` protocol already is the backend-neutral seam.
- The facade accepts only named built-in controllers, so no arbitrary code path reaches recall.
- Programmatic injection remains available on `ControlledRecallPlanner` for harnesses.

**C9 — Typed-graph route deferred to #688.** Making it facade-reachable would feed `typed_graph` hits into the ranking policy's corroboration count. That is a ranking-input change this tranche excludes. It needs #688's typed relation vocabulary and its own ordering evidence.

**C10 — Doctrine guards.** Each is a test or report.
- `recall_control="off"` is byte-identical to the current facade. The `recall()` output must be equal across the existing facade test corpus.
- **With control on:**
  - the admitted set is a subset of the control-off admitted set for the same query and store (bounding can only remove candidates; it never admits);
  - ranking evidence and policy identity equal the default policy's;
  - the #584 M1–M15 expectations and every #580 required unit keep their status, rerun through a control-on ordering report.
- Any change blocks the tranche; it is not re-pinned. The measure is unit status and admitted-order equality, defined in the report.

**C11 — Succession and evidence.**
- The facade change touches the protected surface (`api/surface.py`, and `runtime/recall_control.py` if C2 edits it). Runtime Baseline **v4** is declared through docs/67 Step A:
  - the declaration;
  - the register's `declared_successor` (Step A.3);
  - `declared_changes` via the script;
  - no identity delta, because ranking policy stays 3.2.0;
  - `pyproject_change: null`.
- If #671 later opens work in the same window, it amends this declaration (docs/67 A.6).
- Evidence for publication is a separate gated lanes plan (`-v4`). It must show:
  - **D1:** the default (control off) equals `-v3` exactly;
  - **measured, not gated:** a LongMemEval and AMB `agent_memory_controlled` row.

## Implementation steps (after gate PASS)

1. `recall_control.py`:
   - the `ranking_policy` argument;
   - the outer budget;
   - the actual-stop record and the counted decisions;
   - the fallback path;
   - an `elapsed_ms` measurement.
2. `api/surface.py`: the `recall_control` and `recall_control_budget` parameters, planner construction, the `recall_control` result block, and posture text.
3. Tests: `test_facade_recall_control.py` covering C1, C3, C4 and C10, plus the contract-conformance assertions against the frozen fixture.
4. A control-on ordering report, extending `reference/run_semantic_route_ordering_report.py` with a `recall_control` axis, or a sibling script.
5. Closeout fixture: update rows `jh-06` and `jh-14` to facade reachability, with the evidence pointing at the tests. Record the C7 and C9 deferrals.
6. The v4 declaration; the checker shows TRANSITION. Then a ledger entry, and a merge commit.

## Boundaries

- **Non-goals:**
  - any ranking or policy change;
  - adaptive stopping beyond the target count (JH-07 is T-controller-2);
  - budget allocation (JH-05);
  - the typed-graph route;
  - a learned or hosted controller;
  - consumer-aware packaging (#691).
- **Exclusions:**
  - no default change;
  - no admission change;
  - no benchmark-specific behaviour;
  - no non-deterministic field in any digest.

## Open Questions

None blocking.
