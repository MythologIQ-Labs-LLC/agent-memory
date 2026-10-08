# Project Backlog

This file is the current repository-level work queue. Historical sprint plans, research briefs, and ledger entries explain prior decisions. Live GitHub issues and PRs carry the detailed acceptance criteria for unresolved work. The North Star roadmap event log (`.qor/roadmaps/north-star-best-in-class/events.jsonl`) carries decision and prerequisite state.

The queue is kept small on purpose. Work that is blocked externally, or only interesting for later, must not pose as active implementation.

The previous RC1-era queue (reconciled 2026-09-23 against `3dc11b4`) is superseded by this file. Its RC1 critical path is closed: #427 (production canonical substrate) closed 2026-09-23, #440 (dependency pair re-qualification) closed 2026-09-24, and the developer facade (`AgentMemory.open/remember/recall/correct/forget/history/posture`) is shipped under public contract 1.4.0 with Runtime Baseline v2. That history stays in git and in `docs/META_LEDGER.md`.

## Program posture (owner direction 2026-10-07)

Controlling document: `docs/68-baseline-first-complete-architecture-execution.md`. Program issue: #668. Ledger: Entry #84.

```text
PHASE A - know where we are
    formal external baseline (#694 AgentMemBench/MESA first)
    -> classify deficits, strengths, evidence gaps, unimplemented architecture
    -> freeze the pre-major-runtime baseline

PHASE B - build the complete architecture
    every accepted runtime tranche, prioritized with external evidence
    -> internal conformance -> exact frozen external replay -> comparator delta
    -> architecture interpretation -> next tranche
```

Benchmark deficits set priority and supply acceptance evidence. They do not define the roadmap. Accepted architecture that no benchmark scores is still work.

### Owner rulings (roadmap decision nodes resolved, seq 47-51)

| Node | Ruling |
| --- | --- |
| `decision-capacity-split` | Evaluation-first only long enough to freeze and execute the formal baseline (#694). After that baseline is captured and analysed, substantial capacity returns to the complete runtime architecture. This is not a mandate to implement only benchmark fixes. |
| `decision-temporal-posture` | Primary competitive and currentness lanes use benchmark inputs as provided. No Agent-Memory-only session-date or temporal enrichment. A temporal-enrichment lane may run later only as a separately frozen adapted/diagnostic lane. |
| `decision-embedding-dependency` | A pinned, versioned production local representation provider behind the existing provider abstraction, shipped as an optional extra rather than a base dependency. |
| `decision-hindsight-provider` | One benchmark-agnostic, production-like, exactly pinned Hindsight configuration across all applicable lanes. No benchmark-specific tuning. |
| `decision-eval-credential` | One explicitly authorized, version-pinned reader/judge configuration. The provider, model/version, prompts, evaluator version, budget, credential boundary and reproducibility metadata are bound into every result. Any change produces a new, non-comparable score identity. The credential itself still has to be provisioned. |

### Capacity rule for this cycle

1. Until #694 completes, evaluation work is limited to the formal MESA baseline and the evidence import it needs.
2. After #694, most merged tranches must be runtime tranches. Proposal carried from #674: at least two runtime tranches merged for every evaluation tranche. Exact replays of frozen lanes that a runtime tranche requires count as part of that runtime tranche, not as separate evaluation tranches.
3. A runtime tranche is product-complete only when its behaviour is reachable through `AgentMemory.open()/recall()`, or through the documented public surface it targets. A module that exists somewhere in the repository is not enough.

## Phase A - external baseline (active)

- [x] **#694 (P0)**: untouched formal AgentMemBench/MESA baseline. Executed 2026-10-07 (`docs/69`); M2 judged recall blocked on the judge credential, tracked separately (M1-M6 executed, or classified unsupported/blocked/not comparable), adapter frozen before any score is inspected, per-case M4 currentness failures stage-classified, results imported into the evidence model and the dashboard.
- [ ] **#574 / #600 / #601**: one coherent cross-system comparison programme with strict evidence classes (same-harness reproduced, published external reference, Agent Memory longitudinal, adapted/diagnostic, unsupported, blocked, not run, not comparable). Unavailable evidence is never zero. Retrieval metrics and end-to-end QA are never mixed. There is no universal memory score.
- [ ] **#640**: Mem0 OSS and Hindsight same-harness. Hindsight runs under the frozen configuration from `decision-hindsight-provider`.

North Star comparison coverage:

| Tier | Lane | State |
| --- | --- | --- |
| P0 | AgentMemBench / MESA (formal) | executed (#694); M2 judged recall blocked on credential |
| P0 | LongMemEval_S same-harness retrieval | lanes v2 frozen (`longmemeval-s-retrieval-parity-v2`) |
| P0 | LongMemEval same-harness end-to-end QA | blocked on a provisioned judge/reader credential (`decision-eval-credential` posture set) |
| P0 | BEAM scale tiers | not run |
| P1 | SWE-ContextBench Lite (#467) | harness qualified; external run pending |
| P1 | action-level memory (DolphinBench or equivalent) | not run |
| P1 | PersonaMem | not run |
| Reference | LoCoMo | retrieval-only harness; no external dataset result recorded |
| Reference | longitudinal / field (#388, #408, #496, #501) | longitudinal gates |

## Phase B - complete runtime architecture (follows #694)

The #694 formal baseline is frozen as the pre-major-runtime baseline (`docs/69`, Entry #86). Evidence-informed order, with reasons:

Execution sequence (owner direction 2026-10-07, roadmap events seq 55-60):

1. **Runtime Baseline v4 qualification (#644 shadow controller): done 2026-10-07.** `-v4` lanes accepted (#721: L1 default equals `-v3`, L2 shadow equals default), v4 published (#723, docs/67 B1) and bound (B2: probe run 37671546394, published commit `2501f0f`).
2. **#671 currentness (Runtime Baseline v5): v5 published 2026-10-07; #671 stays open.** Option A is implemented (#726, policy 3.3.0). `mesa-formal-v2` M4 scores 1.000, with all 250 wins `currentness_mechanism` (#728). That result holds under the frozen protocol only and is kept as a regression floor. The `-v5` lanes match `-v4` on every question (1000/1000 + 77/77 EQUAL, 0 limited; #734). v5 was published (B1 #735) and bound (B2: probe run 37692139650, published commit `0110f8e`). General currentness semantics are **not measured** (#732/#733), and G12 is a temporary envelope that stays frozen until the first generalization run.
2a. **#732/#733 independent generalization gate: measured 2026-10-08, result FAIL. #732 remediation now comes before #673.**
   - **Process:** plan gated (Entries #112/#113), corpus frozen (#738, Entry #114), measured once on `main` `db20b4e` against v5 unchanged.
   - **Result:** overall engagement recall **0.000** (0/212). Positives stopped at:
     - 197 at S3, no write-time relation;
     - 15 at retrieval.
   - **Zero-tolerance invariants held:** 0 false engagements, M-flip 320/320, M-attr 0, M-inv 164/164. They hold vacuously, because nothing engaged.
   - **Report:** `reports/benchmarks/currentness-generalization/measurement/`.
   - **Next:** the classification PR (#719 rows; it waits for #733's parent row), then a #732 remediation plan. The remediation is typed write-time change semantics, generic and never G12 case-by-case. It is accepted only on a fresh G6 holdout plus the MESA v2 / #580 / #584 floors.
2b. **#732 remediation (Runtime Baseline v6): v6 published 2026-10-08; the extractor path is UNACCEPTED, and #732 stays open.**
   - **Built:** typed caller propositions and an opt-in model extractor, contract 1.6.0, policy 3.4.0 (#741).
   - **Evidence:** `-v6` lanes EQUAL to `-v5`; `mesa-formal-v3`, extractor off, reproduces v2.
   - **Published:** B1 #745, bound at B2 (probe run 37726966322, published commit `b08cd84`).
   - **Acceptance (R6) is blocked on the owner.** It needs the provider credential and model choice (R7). The provider-freeze record and smoke request come next, then a fresh G6 holdout scored once with the extractor on, plus MESA, #580 and #584 with the extractor on.
   - **If acceptance fails:** a v7 declaration is required.
3. **#673 ranking/fusion: held. The #732 gate FAILED, so #732 remediation must be accepted first.** Iteration 1 was vetoed (`docs/plan-673-route-fusion.md`), and its findings are design inputs. `semantic_retrieval` stays `off` by default (`decision-semantic-default`). No fusion constant is tuned after a score.
4. **#644 controlled recall**, **#688 typed relations**, **#689 metabolism**, **#690 failure memory**, **#691 consumer package**, **#636 composition**. These are accepted architecture that MESA does not score, and they stay in scope.
5. **#596 / #597** interpreter work. Not the M4 bottleneck (interpretation succeeded in 250/250 MESA pairs), but natural-data recognition (#580/#594) still needs it.

Each material tranche replays the frozen MESA runner (successor freeze with only the `agent_memory` block changed) and the relevant lanes. It reports per-axis deltas and the M4 `win_basis` / `primary_stage` distributions.

Retrieval and representation:

- [x] **#669**: semantic/vector route reachable through the facade. Pinned local provider as an optional extra, versioned representation identity, derived and rebuildable vector index, no per-query re-embedding, domain eligibility, provenance.
  Done 2026-10-07:
  - #707 shipped the route, default `off`, under ranking policy 3.2.0.
  - #709 and #711 froze and accepted the `-v3` lanes. D1: the default equals `-v2` exactly. D2: the opt-in route moves no LongMemEval_S metric, as pre-registered.
  - #712 and #713 published and bound Runtime Baseline v3.
  - The movement gate transferred to #673, because the subordinate ordering cannot reach the scored k.
- [ ] **#644**: native controlled recall from the Jev-Mem harvest (call/deadline budgets, stop reasons, route needs, sufficiency, allocation, bounded controller, telemetry).
  - The T-controller shadow seam merged in #715: contract 1.5.0, Runtime Baseline v4 declared, `-v4` qualification in progress.
  - T-controller-2 follows #671 and #673. It covers enforced route, call and deadline budgets, calibrated route needs, sufficiency, adaptive stopping, bounded traversal and a decision cache.
- [ ] **#688**: typed entity/causal relation vocabulary, bounded relation judgments, and typed graph traversal reachable through the facade.
- [ ] **#673**: post-admission route fusion, then a separately versioned reranker if justified. Ranking orders admitted candidates and never admits.

Temporal, currentness and semantics:

- [ ] **#671**: read-path currentness, option A (`interpreted_cross_fact` applicability limitation), Runtime Baseline v5. Option D (governed auto-application with receipts) is a separate ADR afterwards. Recency never becomes authority.
- [ ] **#596**: natural proposition recognition without weakening abstention.
- [ ] **#597**: canonical proposition slot/value boundaries.
- [ ] **#586**: explicit bounded exception/override precedence.

Lifecycle, cognition and composition:

- [ ] **#689**: metabolism (consolidation/maintenance) in the runtime caller path, using the non-destructive proposal vocabulary.
- [ ] **#690**: governed failure memory composed into recall admission evidence.
- [ ] **#691**: consumer-aware memory package beyond a ranked k-prefix.
- [ ] **#636**: heterogeneous memory composition as an executable runtime architecture.
- [ ] **#410**: composition umbrella. Every mechanism described as native or qualified must be reachable through the public facade, or its record must say otherwise. This includes the baseline-v2 `native_qualified` drift for vector, typed-graph and metabolism.

Implementation profile:

- [ ] **#602**: Rust qualification where it earns its role through semantic parity, assurance, performance, lifecycle parity and reproducibility. It never outranks missing memory behaviour.

Fundamental behaviours that every tranche must preserve: semantic, epistemic, procedural and predictive memory; correction; supersession; forgetting and tombstones; reconstructable history; provenance; identity; scope and isolation; authority; restart safety; governed admission; lifecycle; persistence; recovery; determinism; public developer usability.

Load-bearing invariants:

```text
relevance != currentness        ranking != admission
newer != superseding            interpretation != authority
inference != mutation authority benchmark score != truth
```

## Platform and governance

- [ ] **#662**: Phases 2-4 landed (`prereq-ci-cost` resolved). Phase 1 workflow-estate budget work continues. Stale-run cancellation PR #665 is open.
- [ ] **#635**: converge Gauntlet v1 and Runtime Baseline.
- [ ] **#554 / #524**: system-neutral qualification and benchmark-neutral evaluation subsystem.
- [ ] **#565 / #556**: project-model and commons/runtime boundary documentation.
- [ ] **#674**: closes once this backlog is reconciled (done here), the capacity split is recorded (done here) and the first runtime tranche (#669 or the evidence-justified first tranche) has merged with lane evidence.

## Dependency qualification

Bare Dependabot bumps of qualified interoperability dependencies cannot be merged one file at a time. The #375/#440 precedent applies. Open bumps #654 (`agentrust-trace` 0.11.0), #655 (`agent-manifest` 0.15.0) and #656 (`cryptography` 50.0.2, under `/reference`) need a version-exact qualification change before merge. #599 (actions group) follows the workflow-policy checks.

## External / longitudinal gates

- **#361, blocked external**: needs an authorized live Cloudflare/DashClaw traversal.
- **#388 / #408 / #496 / #501, longitudinal**: need field evidence. No speculative implementation slices before that evidence exists.
- **#495**: live cognitive-classification providers need provisioned providers.
- **#696, future**: benchmark evidence console. Not active this cycle.

## Repository hygiene rule

Every open issue or PR must have one of:

1. an executable next implementation or review step;
2. an explicit external or longitudinal blocker that justifies keeping it open;
3. a semantic dependency-qualification reason.

Anything else leaves the active queue and is reopened when it becomes executable. Age alone is not a reason to close work, but age without a next action is a backlog smell and must be reconciled. Before a historical branch is deleted, it must be compared against `main` for unique commits.

---

_Last reconciled against `main` `2d852d3814333a998aec40113c71f29b26ad8aa4` on 2026-10-07._
