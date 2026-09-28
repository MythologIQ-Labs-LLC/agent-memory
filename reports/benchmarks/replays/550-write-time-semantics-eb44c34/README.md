# #550 external replay: policy 3.1.0 (write-time semantics) vs canonical policy 3.0.1

Evidence class: external benchmark evidence, bounded to these corpora and retrieval profiles. It is not proof of general superiority or correctness. ADR-039 remains **Proposed**.

| item | value |
| --- | --- |
| candidate | `eb44c347ff0c24d458f4dd8aedc269e7b0d700dc` (branch `implementation/550-proposition-semantics`), clean runtime tree |
| canonical | `reports/benchmarks/replays/576-deterministic-bm25/*8bd6c91*` (policy 3.0.1; runtime equal to `main` `550abf0` for these benchmarks) |
| AgentMemBench | `mazaiying/AgentMemBench@186c9a54`, `data/memdialogue_v2.jsonl` sha256 `33632710ae6495b95724df455ff6f9947d231ee68ebc0ef10eb8291fd55ca2a6` (real payload) |
| LongMemEval_S | `xiaowu0162/longmemeval-cleaned@98d7416c`, `longmemeval_s_cleaned.json` sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, 500 questions |

These are the same bytes as the #583 replay; both digests were verified before any run.

## Results

* **AgentMemBench** (all phases, seeds 0 and 1): `compare-agentmembench-eb44c34-seed{0,1}-vs-8bd6c91.json` are both **IDENTICAL**, with 0 non-timing differences in every dimension and governance tally. `agentmembench-traces/`: all 2,051 per-search ordered results and every BM25 score bit are identical to the canonical #576 trace (`amb_order_trace.py`).
* **LongMemEval_S** (`longmemeval-s-full-eb44c34-seed1.json` + `.rows.json.gz`): `compare-lme-s-eb44c34-seed1-vs-8bd6c91.json` is **IDENTICAL**. All 53 checks pass; 3,000/3,000 rows are semantically identical with 0 rank differences. Governance, failures, and currentness are unchanged.
* **Changed rows:** none, so no row falls into any classification (`INTENDED_550_EFFECT`, `NUMERICAL_ONLY`, `UNRELATED_DRIFT`, `FAILURE_OR_GOVERNANCE_CHANGE`, `UNEXPLAINED`). This is expected: neither harness declares `observed_at`, so no interpreted self-validity window resolves, and write-time proposals are never applied.
* **LongMemEval_M:** not run and not required. No escalation trigger holds, and S characterizes the affected population exactly (zero rows).
* **Typed-carrier coverage** (`lme-s-carrier-coverage-eb44c34.json`, `lme_carrier_coverage.py`): over 93,931 unique user turns, 14.5% of propositions are known, 47.6% ambiguous, and 37.9% unknown. The typed aspect marker carries every #583 cue occurrence: `currently` 551/551, `planning to` 2,076/2,076, `going to` 1,314/1,314.

## Timing

Wall times in these reports are not comparable with the canonical ones. Idle timing pairs against `main` are recorded in docs/61 §5: AgentMemBench wall +15%, and retrieval read p50 15.0 -> 17.7 ms. The cause is attribute decoding in candidate generation, and a follow-up is proposed.
