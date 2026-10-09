# North Star frontier obligations: evidence-led, complete-architecture execution

**Owner:** #668; controlling posture: `docs/68-baseline-first-complete-architecture-execution.md`. **As-of:** 2026-10-09. **Stage:** read-only objective projection; does not promote ADR-043, declare baseline v7, decide a benchmark score, or authorize runtime mutation.

## The program's actual target

Best-in-class is a **nine-axis capability frontier**, not one leaderboard. The Coverage Atlas (§7) defines the nine families: A ingestion, B retrieval, C temporal, D lifecycle, E governance, F durability/scale, G cognitive utility, H multi-source/multi-agent/multimodal, I evaluator validity. Every accepted material deficit and every declared external gap needs an accountable objective, a general-memory architectural owner and explicit release evidence. Winning among two weak comparators is **not** enough; a frontier may remain inadequate.

**Canonical registries**
- `data/benchmark-frontier-objectives.json`: 29 named objectives, each with capability family, benchmark family, native metric, architecture, issues, evidence source and release gate. This is a *planning registry*, never a benchmark input or gold map.
- `reports/benchmarks/deficits/current.json`: accepted concrete current deficit evidence, including family-level currentness failures, untouched by this implementation.
- `reports/benchmarks/dashboard/current.json`: canonical accepted baseline and lane identities, not a universal ranking.
- `scripts/build_frontier_objectives.py`: deterministic projection, comparable-relative-to-observed-peer only, rejects ownerless deficits and loss of blocked-state or authority guard. Run `python scripts/build_frontier_objectives.py --output /tmp/frontier-obligations.json`. Never write to the inputs from this tool.
- `tests/test_frontier_objectives.py`: 17 synthetic and source-integrity checks executed in the existing doctrine workflow, including all nine families, all currently accepted deficit rows, comparator direction, unmeasured states, exact metric ID, live ledger drift, reproducibility and no score/mutation authority.

## Reconciled measured posture (no invented rankings)

These are exact lane-specific observations from accepted repository evidence. No global system ranking is asserted.

| Capability | Accepted measurement | Comparison interpretation | Required next evidence |
| --- | --- | --- | --- |
| LongMemEval_S **session** recall_all@5 | Agent Memory 0.823 vs Mem0 OSS 0.809 on the accepted same-harness lane | Ahead among observed systems, not an entire market rank | Longer/deeper k, currentness/cost trade-off, broader same-harness comparators |
| LongMemEval_S **turn** recall_all@50 | Agent Memory 0.859189 vs Mem0 OSS 0.894988 | Behind observed peer (P1) | #673 retrieval/reachability/fusion causation; frozen replay and safety floors |
| AMB PrecisionMemBench retrieval | Agent Memory 4/43 active passes; mean precision 0.18 | Best reproduced control but **inadequate** (P1) | #719 stage attribution, #644/#673/#691 as justified; general precision across independent family |
| Formal MESA M4 successor | 250/250 currentness-based wins | Frontier in that exact formal protocol; not general currentness proof | Preserve 1.000 as a floor, independently demonstrate #732 generalization |
| #732 currentness generalization v1 | 0/212 legitimate engagement, no false structural engagements | Architecture gap (P1); zero safety failures are vacuous | Typed, generalized proposition/change identity, **unseen** holdout, no G12 patching |
| #594 natural Part R | known recall 0.148148, known precision 0.800 | Over-ambiguity/slot-value weakness (P2); native score only | #596/#597 general interpreter improvement + independent holdout, preserve abstention |
| Formal MESA M2 end-to-end judged QA | blocked on authorized pinned credential | **No judged accuracy value** | Frozen reader/judge, no comparing substring proxy to model-judged accuracy |
| LongMemEval_M | session recall_all@5 0.708831; turn 0.532220 | External bounded retrieval, no same-harness peer rank | Reproduced same-harness comparisons on the same M selection and return budget |
| SWE-ContextBench Lite | synthetic smoke only; external projection missing | **Blocked**, not scored | #467 exact external evaluation projection and provenance |
| BEAM, PersonaMem, memory-to-action, LoCoMo end-to-end, longitudinal | not run / partial diagnostic / qualification needed | **Unmeasured**, not poor performance and not a win | Qualification, fixed selection, matched comparators, task-level and scale metrics |

Preserve current accepted strong governance/durability evidence as regression floors while extending genuinely independent multi-writer and adversarial evaluation. Published scores (Hindsight, Mem0 managed, Zep, Cognee, etc.) are useful **directional reference pressure**, not rankings against Agent Memory's retrieval@k.

## Architecture alignment and implementation order

This complements #757's evaluation-only trust evidence, but does **not** make that stack a production memory capability. Do not allocate most future engineering effort to another signature/benchmark scaffolding slice while the accepted memory runtime remains incomplete.

### Gate 0: preserve the ruler and safety

- Keep source protocol/revision, input selection/digest, judge and model identity, returned `k`, context budget, and execution environment bound per score.
- Keep retrieval, answer/task success, temporal, governance and efficiency as **separate metrics**, not a scalar.
- New runner/lane profiles need preregistration, independently authored generalization cases, zero-tolerance safety controls and no frozen-label leakage.
- A best-in-local-comparators result creates **both** a regression floor and a harder-pressure obligation.
- All 25 currently accepted deficit ledger entries must remain owned by at least one objective; new accepted deficits fail CI coverage until assigned.

### Gate 1: capability restoration / correctness

1. **#732** is the largest correctness/generalization deficit: typed write-time assertion/change/identity/cardinality semantics with guarded read-time applicability. R6 is blocked until provider and independent holdout are approved. Do not reverse-engineer or reuse the frozen holdout.
2. **#596/#597** isolate natural-language recognition and slot/value-boundary accuracy. Don't fit aliases on accepted Part R scores.
3. **#757** remains a proposal-only trust/persistence/correction architecture frontier, distinct from P.A.I. Authenticated roots, revocation, false-link correction and semantic identity are prerequisites before safe production integration.

### Gate 2: retrieve the right evidence with bounded work

4. **#644**: turn today's non-authoritative shadow route plans into *optional, enforced* call/route/deadline budgets and inspectable sufficiency/stop reasons, without allowing controller suggestions to bypass governance.
5. **#673**, after the #732 safe-generalization gate: post-admission hybrid fusion, then a separately versioned reranker if causal ablations justify it. The semantic-only gold item ranking last (116/116) suggests a reachability/ordering barrier; avoid treating this diagnosis as proof a particular fusion constant is optimal.
6. **#688**, **#691**: typed graph and relation judgments plus consumer-aware delivery budgets. A ranked prefix is not task-ready memory.
7. **#690**, **#689**, **#636**: governed failure/experience memory, non-destructive metabolism and heterogeneous composition. These remain necessary even if current benchmarks don't reward them.

### Gate 3: prove quality, scalability and task impact

8. Independent end-to-end QA (MESA M2, LongMemEval, LoCoMo), personalization (PersonaMem), coding reuse (SWE-ContextBench), memory-to-action (DolphinBench equivalent), long-horizon scale (BEAM), and realistic field/longitudinal pressure. No invented ranks when credentials or source rights are absent.
9. Measure cost/latency/context utilization, calibrated abstention, stability, replay, deletion completeness, poisoning resistance and multi-agent isolation **on the same task and fixed protocol**. Seek a non-dominated operating point, not merely higher recall.
10. For each merged runtime tranche: preregister causal hypothesis → implement reachable through documented facade → native and adversarial tests → exact frozen primary replay → orthogonal held-out family → cross-benchmark, governance, latency, restart regression → review successor baseline. If one gate fails, keep the deficit open and loop.

## Hard-stop invariants

```text
evidence ranking != global market ranking
frontier against observed comparator != task adequacy
published reference != same-harness peer
metric named the same != protocol-comparable
currentness != recency
ranking != recall admission
semantic inference != authority
candidate memory != accepted memory
no data != zero
evaluation throughput != implemented runtime capability
```

This document is a strategy and a code-backed objective registry. It does not claim that any current benchmark deficit has been remediated. The next material runtime tranche should be selected from Gate 1/2 using the existing baseline governance, not by modifying benchmark cases.
