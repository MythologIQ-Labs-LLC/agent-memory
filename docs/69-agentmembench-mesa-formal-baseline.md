# AgentMemBench / MESA formal baseline (#694)

Status: **protocol frozen before score inspection**, 2026-10-07. The results section is added by a later commit, after execution. This document's protocol sections must not change after that.

Related: #694 (owner issue), #668, #600, #601, #574, #671. Posture: `docs/68-baseline-first-complete-architecture-execution.md`. Owner rulings: roadmap seq 47-51 (`decision-temporal-posture`, `decision-eval-credential`).

## Why a second AgentMemBench profile

The existing profile `agent-memory-agentmembench-memdialogue-operational-v1` (#517, PR #533; runner `reference/run_agentmembench.py`) re-expresses the upstream phases. It replaces the LLM-judged retrieval metric with a profile-local exact-source recall and is classified `external_adapted`. Its new-fact-first 0.20 / staleness 0.80 signal is a risk indicator, not a formal MESA result.

The formal profile `agent-memory-agentmembench-mesa-formal-v1` (runner `reference/run_agentmembench_formal.py`) does **not** re-express the workloads. It imports the pinned upstream harness module from a digest-verified checkout and calls the upstream phase functions with the upstream default arguments. Agent Memory takes part only through the upstream five-method adapter protocol.

## Frozen identity

Freeze manifest: `reference/fixtures/benchmarks/agentmembench/mesa-formal-v1-freeze.json`. The runner refuses to run unless every digest below is recomputed and matches.

| Item | Binding |
| --- | --- |
| Upstream repository | `mazaiying/AgentMemBench` @ `186c9a54edd47aae42d8b6990520f8e902b60303` (default-branch HEAD on 2026-10-07; same revision as the adapted profile) |
| Harness | `agentmembench/evaluation/unified_benchmark.py`, sha256 `d0d40712…94df` |
| Dataset | `data/memdialogue_v2.jsonl`, 9,170 records, sha256 `33632710…a2a6` (ODC-By 1.0; repository redistribution posture `linked_only`) |
| Published formal results | `results/formal/SHA256SUMS`, sha256 `8322f56d…c68e`; upstream `validate_artifact` passes (29 files, 9,170 records) |
| Workload arguments | upstream defaults, identical to every published seed-2027 file: 1,000 retrieval records in groups of 10, top-k 5, seed 2027, 250 conflict pairs, 100 isolation users × 5 facts, 200 deletion records, 200 concurrency records at workers 1/4/8/16, scales 100/1,000 with 200 read queries, 5 warm-up writes |
| Runner | sha256 recorded in the freeze; a changed runner is a new protocol identity. The upstream default arguments are hard-coded in the runner and asserted equal to the freeze |
| Agent Memory runtime | git tree of `reference/agentmem_ref` `771447a4…` (runtime, ranking policy, interpreter, admission, packaged profile), ranking policy `multi-route-default` 3.1.2, contract 1.4.0, Python 3.11, pinned `numpy`/`openai`/`qdrant-client`/`httpx`/`jsonschema`/`cryptography`/`rfc8785`. The run refuses on any mismatch and on any dirty or untracked file in the repository |
| Upstream checkout | must be pristine including git-ignored files (it is placed on `sys.path`); bytecode writing is disabled; dataset meta sha256 verified |
| Judge (M2) | Qwen2.5-14B-Instruct through the upstream `JUDGE_PROMPT` (sha256 `a1865149…6081`) and `judge_retrievals` (temperature 0, max_tokens 32, JSON object) |

## Agent Memory participation (frozen adapter)

- Public facade only: `AgentMemory.open`, `remember`, `recall(budget=limit)` (contract 1.4.0 return budget), `forget`, `close`.
- One tenant. Each upstream `user_id` is its own governed scope and required isolation domain. Isolation is enforced by canonical recall admission, not by an adapter filter.
- `search` returns the stored text of the `returned` ranked admitted prefix. `delete` is the facade default `forget` (governed tombstone).
- Supplied: benchmark text and query only. Withheld: temporal metadata, reference time, temporal intent, session dates, logical memory references, gold data, ranking variants. This follows `decision-temporal-posture` (declare to none).
- Ranking: the runtime default (`multi-route-default` 3.1.2 at freeze time).
- Observation only: the adapter keeps a per-search trace for conflict-phase users and, after the phase, reads the write-time interpretation of those facts. Neither read changes stored, admitted, ranked or returned state.

## Retrieval judging and the credential boundary

Upstream `recall_at_k` is LLM-judged. The upstream judge maps every transport failure to `hit: false`, so running it without an authorized endpoint would publish a fabricated 0.0. The formal run therefore separates execution from judging:

1. Execution stores, for every query, exactly what Agent Memory retrieved. Judge-derived fields are stripped, not zero-filled.
2. `--judge` later applies the frozen judge through the upstream `judge_retrievals` to the uncommitted raw report.
3. Until an authorized judge is provisioned (`decision-eval-credential`), judged recall is **blocked**.
4. A judge run still refuses to emit a score unless every non-empty row received a parsed verdict. Upstream would silently score a failed row as a miss, so if the parsed-response count differs from the number of non-empty rows the status stays `blocked` and the failure count is reported. The run also records a preflight request and the served model ids, and verifies the raw retrieved items against the committed per-item digests.

A judge other than Qwen2.5-14B-Instruct creates a new, non-comparable score identity. For a same-judge comparison, the five published upstream detail files must also be re-judged with it.

Deterministic diagnostics (`mesa-m2-deterministic-diagnostics-1.0.0`, adapted/diagnostic class, never substituted for judged recall), computed identically for Agent Memory and for the five published upstream detail files:

- `answer_substring_hit_rate`: the casefolded reference answer occurs in any top-5 item. Its agreement with each upstream system's published judge hits is reported as calibration.
- `source_text_hit_rate`: the record's own text is retrieved verbatim. Not cross-system comparable, because LLM-extracting systems rewrite memories.
- `empty_retrieval_rate`.

The same seed and `load_records` must reproduce upstream's selection. The run reports the `source_ids_sha256` of its selection next to each published file's.

## M4 failure-stage classification (frozen)

Classifier `mesa-m4-stage-classifier-1.1.0` (`classify_conflict_case`; adapted/diagnostic attribution of the exact upstream metric) checks, for each of the 250 pairs, the conditions a currentness-correct top-1 requires, in pipeline order:

```text
write_admission -> candidate_generation -> admission -> write_interpretation
  -> identity_slot_resolution -> conflict_supersession_reasoning
  -> temporal_applicability_currentness -> ranking_fusion
```

- Every case records all unmet stages. For a miss, the primary stage is the first unmet one.
- The currentness condition holds when the old fact falls in the demoted temporal-applicability tier for the query's intent mode, or when an explicit-current constraint applied to the pair. A `state_change_candidate` relation, including one reached by explicit termination, satisfies the interpretation and slot conditions.
- `decisive_stage` is the first ranking stage that separated the two facts. `win_basis` for a hit is one of `uncontested` (old fact not admitted), `currentness_mechanism`, `temporal_order_tiebreak` (newer-first among relevance ties), `lexical_ordering` or `undetermined`. Correct for a non-currentness reason is not currentness capability.
- The classifier's top-1 outcome counts must reproduce the upstream `new_fact_rate` and `staleness_rate` exactly (`upstream_consistency`).
- Two #694 taxonomy stages cannot be exercised by this workload. The answer/evaluator layer cannot, because the evaluator is token containment. Unsupported semantics cannot be separated from extraction misses, so both are reported together under `write_interpretation`.

## Axis classification plan

| Axis | Source | Expected class |
| --- | --- | --- |
| M1 write efficiency | retrieval-phase write latency and materialization; concurrency throughput | exact workload, environment-bound (CPU-only in-process runtime vs GPU-hosted LLM-coupled services) |
| M2 retrieval quality | retrieval phase | executed; judged recall blocked pending an authorized judge; diagnostics adapted |
| M3 scalability | scale phase | exact (recall@3); environment-bound (latency) |
| M4 temporal consistency | conflict phase | exact |
| M5 isolation and privacy | isolation and deletion phases | exact (search visibility; deletion is a governed tombstone) |
| M6 LLM portability | none | not comparable: upstream ships no executable M6 protocol (the published figure plots a constant value for all five systems). No M6 result is claimed for any system |

## Deviations register

The freeze lists every deviation from an untouched upstream run:

- **D1** the judge is substituted by a capture, and the judge-derived fields are absent;
- **D2** unused endpoints are recorded as `not_used`;
- **D3** an `agent_memory` evidence block is added (do not run upstream `aggregate_unified.py` on this report);
- **D4** retrieval details are committed as a `linked_only` projection;
- **D5** the conflict-phase timed calls include O(1) observation appends, while digesting happens at reset, outside timing;
- **D6** the run uses a CPU-only Python 3.11 container, so latency depends on the environment.

## Pre-score gate

The independent pre-score audit, iteration 1, returned VETO on three grounds:

1. the M4 win attribution credited currentness wrongly in both directions;
2. the Agent Memory runtime was neither bound nor enforced, and no deviations were registered;
3. the judge path could publish a deflated score.

Each ground was remediated before any MESA workload ran.

The deterministic diagnostics over the five published upstream files were computed before Agent Memory's run (`reports/benchmarks/agentmembench-mesa-formal/upstream-reference-diagnostics.json`). Upstream `load_records` reproduces the exact published selection for all five systems (`event_type` and `source_id` match on every row). The substring diagnostic is conservative: across the five systems, at most 0.2% of rows count as a hit when the published judge said miss.

## Stop lines

No adapter or runtime change after score inspection. No temporal enrichment in this lane. No gold-aware transformation. No budget change. Unsupported or blocked operations are never recorded as zero. A benchmark score is not memory authority.

## Reproduction

```bash
git clone https://github.com/mazaiying/AgentMemBench && git -C AgentMemBench checkout 186c9a54edd47aae42d8b6990520f8e902b60303
python3.11 -m venv .venv && .venv/bin/pip install numpy==2.4.6 openai==2.44.0 qdrant-client==1.18.0 httpx==0.28.1 -r reference/requirements.txt
PYTHONPATH=reference .venv/bin/python reference/run_agentmembench_formal.py --upstream-root AgentMemBench \
  --output agent_memory_formal_s2027_9170.json --raw-output raw.json
PYTHONPATH=reference .venv/bin/python reference/run_agentmembench_formal.py --upstream-root AgentMemBench \
  --reference-diagnostics upstream-reference-diagnostics.json
```
