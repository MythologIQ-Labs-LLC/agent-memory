# Concurrent runtime feedback and independent qualification

**Status:** Proposed engineering operating procedure for #819 / #719. No new runtime acceptance or benchmark score authority. This document is an engineering workflow, not an ADR or successor baseline.

## Stop serializing on full benchmark completion

There are four independent clocks:

1. **Engineering:** isolated implementation and fast local regression tests.
2. **Independent acceptance:** exact frozen source, independently sealed hidden cohort, safety, full-suite and benchmark regressions.
3. **Competitor qualification:** lengthy native system ingestion, full LongMemEval session/turn and repeated third-party runs.
4. **Release integration:** compatibility/version reconciliation, security ancestry, required protection and clean installation.

**Development and discovery may proceed concurrently. Acceptance and release remain sequential and evidence-gated.** C5 may be investigated while C4 is frozen and being reviewed, but C5 cannot use C4's private cohort or claim its provisional scores as accepted. If a C4 verdict changes the required baseline, C5 must reconcile with that finding before acceptance. The full Hindsight, Cognee, Jev-Mem, Graphiti and LangMem runs must not gate independent runtime diagnosis.

## Bounded local feedback

`scripts/run_runtime_fast_feedback.py` runs selected **existing** native unit/conformance suites, rather than simulating benchmark scores or reusing exposed hidden gold.

```bash
python scripts/run_runtime_fast_feedback.py --focus retrieval --max-total-seconds 180
python scripts/run_runtime_fast_feedback.py --focus temporal --max-total-seconds 180
python scripts/run_runtime_fast_feedback.py --focus governance --max-total-seconds 180
python scripts/run_runtime_fast_feedback.py --focus all --max-total-seconds 360 --output /tmp/agent-memory-fast-feedback.json
python -m unittest discover -s tests -p 'test_runtime_fast_feedback.py' -v
```

| Focus | Existing suites | Purpose |
| --- | --- | --- |
| retrieval | `test_query_driven_recall.py`, `test_multi_route_recall.py` | Native candidate reachability, routing and refusals |
| temporal | `test_cross_fact_currentness.py`, `test_api_history_posture.py` | Currentness and historical query behavior |
| governance | `test_scope_governance.py`, `test_deletion_authority.py` | Scope/authority and deletion regressions |
| all | All six above | Wider diagnostic check, **not full suite** |

The default per-suite limit is 60 seconds. Exceeding a time limit or failing an individual suite returns nonzero and is explicitly represented in the JSON receipt. On POSIX, a timeout terminates the spawned test process group to avoid orphan subprocesses competing with native benchmark jobs; on Windows only the direct unittest process is terminated, so use an external process-tree supervisor if suites launch child workers. A Git SHA, clean/dirty state, commands, selected suite results, durations and failure logs are recorded where possible. Only run with synthetic data and do not publish receipts that contain secrets. The wrapper itself does not enforce network isolation; use a sandbox when the environment or tests require it.

**A PASS means only that the selected local tests passed.** The receipt always says `qualification_effect=none`, `comparison_eligible=false` and `runtime_baseline_activated=false`. Never treat it as a complete green suite, hidden evaluation, independent review or acceptance of a default runtime policy.

## Delivery stages and their blockers

| Stage | Required evidence | What is allowed to proceed |
| --- | --- | --- |
| Hypothesis | Reproduced general defect, synthetic controls, mechanism proposal | Parallel isolated work; no need to wait for competitors |
| Engineering checkpoint | Local focused tests, explicit remaining limitations | Subsequent engineering tasks and disjoint hypotheses |
| Frozen candidate | Immutable SHA, preregistration, exact mechanism, no gold exposure | Independent reviewer starts; author may start next isolated hypothesis |
| Independent acceptance | Previously unseen sealed cohort, cross-benchmark regressions, governance/safety, full suite, latency and durability | Only the accepted candidate can advance to integration |
| Runtime release | Coherent security lineage, successor baseline, contract versions, clean install and protected checks | Publication/default adoption, without branch-protection bypass |
| Competitor admission | Native source/mode/model identity, full completed denominators, repeatability and independent review | Only validated comparable peer scores reach the leaderboard |

## CPU scheduling and stop lines

- Give highest priority to security or correctness blockers and **finishing an already sealed candidate evaluation**.
- Keep focused deterministic tests responsive. When work shares a 4-vCPU host, run only when there is spare capacity or reserve one CPU where practical.
- Let valid pinned comparator runs continue in the background. A two-hour watcher expiring is **not** evidence that a four-hour native run failed.
- Do not start additional local LLM ingestion alongside heavy Graphiti/LangMem/Hindsight/Letta jobs merely because an agent session is idle.
- New exploratory peers require an explicit setup smoke, likely total runtime/CPU budget and stop rule. Resource starvation is `blocked/partial`, not a zero score or disqualifying product failure.
- Incremental verified subset reports are allowed **only with subset denominator and candidate status**. A completed cohort's final score is independent of an unrelated peer's still-running experiment.
- No model paid usage, GitHub Actions fan-out, new public score promotion or arbitrary closing of #819/#810.

## Three separate runtime deficits in the current evidence

1. **Paraphrase and multi-evidence completeness:** necessary facts are missing from the output set, possibly at candidate discovery, lexical filtering or return budgeting. Evaluate on newly authored independent examples and irrelevant-neighbor negatives.
2. **Genuinely nonlexical multi-hop:** 0/16 across tested runtimes when the intermediate fact shares no content words with the question. Test governed multi-step candidate traversal and false-link, revoked and cross-scope edges. Never infer that a v2 lexical shortcut demonstrated real bridging.
3. **Temporal conflicting-statement ordering:** 0/16 newer-first across tested runtimes. Distinguish recency-aware *ranking* from authorized *supersession*. Newer timestamps must not become write/overwrite authority.

Work these as **distinct hypotheses**, not another unmeasured relevance-threshold adjustment. Keep `ranked_prefix` default while successors remain experimental, and preserve the exact trust, scope, forgetting and deletion boundaries.

## Throughput metrics

Track per change: last frozen SHA, time to first reproducible failing test, time to frozen candidate, independent-review wait, final disposition, time to merged integration, compute consumed and what stage blocked. A long external peer run is a benchmark lane's elapsed time, **not** the time to the next runtime engineering insight.

A result that is `candidate`, `not_run`, `blocked`, or `not_measured` must remain exactly that. No hidden cohort may be retroactively treated as pristine after its category findings have been revealed.
