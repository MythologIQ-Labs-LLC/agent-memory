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
4. A judge run first re-verifies the arguments, the runner, the upstream checkout and the committed report's freeze and runner digests. It rebuilds each query and reference answer from the frozen selection, never from the raw file, and checks every row against the committed report. It refuses to emit a score unless every non-empty row received a parsed verdict with a boolean `hit`. If the endpoint serves any model other than the frozen one, the status is `judged_non_comparable_model` and no comparable recall is reported. Upstream would silently score a failed row as a miss, so if the parsed-response count differs from the number of non-empty rows the status stays `blocked` and the failure count is reported. The run also records a preflight request and the served model ids, and verifies the raw retrieved items against the committed per-item digests.

A judge other than Qwen2.5-14B-Instruct creates a new, non-comparable score identity. For a same-judge comparison, the five published upstream detail files must also be re-judged with it.

Deterministic diagnostics (`mesa-m2-deterministic-diagnostics-1.0.0`, adapted/diagnostic class, never substituted for judged recall), computed identically for Agent Memory and for the five published upstream detail files:

- `answer_substring_hit_rate`: the casefolded reference answer occurs in any top-5 item. Its agreement with each upstream system's published judge hits is reported as calibration.
- `source_text_hit_rate`: the record's own text is retrieved verbatim. Not cross-system comparable, because LLM-extracting systems rewrite memories.
- `empty_retrieval_rate`.

The same seed and `load_records` must reproduce upstream's selection. The run reports the `source_ids_sha256` of its selection next to each published file's.

## M4 failure-stage classification (frozen)

Classifier `mesa-m4-stage-classifier-1.2.0` (`classify_conflict_case`; adapted/diagnostic attribution of the exact upstream metric) checks, for each of the 250 pairs, the conditions a currentness-correct top-1 requires, in pipeline order:

```text
write_admission -> candidate_generation -> admission -> write_interpretation
  -> identity_slot_resolution -> conflict_supersession_reasoning
  -> temporal_applicability_currentness -> ranking_fusion
```

- Every case records all unmet stages. For a miss, the primary stage is the first unmet one.
- The currentness condition holds when the old fact falls in the demoted temporal-applicability tier for the query's intent mode, or when an explicit-current constraint applied to the pair. A `state_change_candidate` relation, including one reached by explicit termination, satisfies the interpretation and slot conditions.
- `decisive_stage` is the first ranking stage that separated the two facts. `win_basis` for a hit, and `loss_basis` for a stale result, take one of these values:
  - `uncontested`: the old fact was not admitted.
  - `currentness_mechanism`: currentness separated the pair.
  - `content_identity_tiebreak`: under explicit current intent, two unknown-basis facts that tie on every relevance stage are ordered by a time-neutral content digest (`temporal_order_constraints`). This applies even when that order happens to equal newer-first.
  - `temporal_order_tiebreak`: newer-first among relevance ties, outside that profile.
  - `lexical_ordering`: a relevance, route, corroboration or exact-identity stage decided.
  - `undetermined`: the decisive stage is not in the mapping.

  Correct for a non-currentness reason is not currentness capability.
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

Iteration 2 returned VETO on two grounds:

1. a time-neutral content-digest tiebreak could be credited as recency;
2. the judge path did not re-verify the protocol or the gold inputs.

Both were remediated.

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

## Results (executed 2026-10-07, after the gate PASS)

Status of this section: **formal baseline executed; M2 judged recall blocked**. Everything above this section is the frozen protocol and is unchanged by the run.

Run identity: Agent Memory `7b041a741e80a29f6911794a4917b414c0dab032` (clean worktree, verified), runtime tree `771447a4…`, ranking policy `multi-route-default` 3.1.2, contract 1.4.0, Python 3.11.17 with every pinned package verified, upstream `186c9a5` (pristine including ignored files), freeze runner sha256 `58b2fced…`. Wall time about 42 s on a CPU-only container. Report: `reports/benchmarks/agentmembench-mesa-formal/agent_memory_formal_s2027_9170.json` (linked-only; verified to contain none of the 2,699 distinct MemDialogue strings of the run). The selection digest `db563c1f…` equals the selection that upstream `load_records` reproduces for all five published systems.

Comparison columns are **published external reference under the identical frozen protocol** (`upstream-published-reference.json`). They are not reproduced here, they run in a different environment, and their recall@5 is LLM-judged.

| Axis / metric | Agent Memory | Naive RAG | Mem0 | LangMem | Graphiti | Letta | Class |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M1 write success (materialization) | **1.000** | 1.000 | 0.797 | 0.475 | 0.841 | 1.000 | exact workload |
| M1 write mean latency (ms) | **6.2** | 44.6 | 1,078.7 | 4,986.6 | 8,302.6 | 4,735.4 | environment-bound |
| M1 read mean latency (ms) | **8.1** | 43.3 | 41.5 | 39.7 | 83.6 | 2,205.1 | environment-bound |
| M1 concurrency op success @16 | **1.000** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | exact |
| M1 throughput @16 (ops/s) | **151.7** | 15.6 | 6.3 | 4.5 | 1.3 | 1.2 | environment-bound |
| M2 recall@5 (LLM-judged) | **blocked** | 0.966 | 0.818 | 0.286 | 0.687 | 0.982 | blocked: no authorized judge |
| M2 answer-substring hit@5 (diagnostic) | **0.728** | 0.794 | 0.421 | 0.162 | 0.222 | 0.626 | adapted/diagnostic |
| M2 source-text hit@5 (diagnostic, verbatim stores only) | **0.899** | 0.971 | n/c | n/c | n/c | n/c | adapted/diagnostic |
| M3 recall@3 at 100 / 1,000 facts | **1.000 / 1.000** | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | exact |
| M3 read mean latency @1,000 (ms) | **7.8** | 44.6 | 40.7 | 58.4 | 45.5 | 1,981.6 | environment-bound |
| M4 new-fact rate | **0.200** | 1.000 | 0.900 | 0.680 | 0.004 | 0.996 | exact |
| M4 staleness rate | **0.800** | 0.000 | 0.024 | 0.104 | 0.984 | 0.000 | exact |
| M4 dual-version rate | **0.000** | 0.000 | 0.876 | 0.024 | 0.000 | 0.000 | exact |
| M5 cross-user leak rate | **0.000** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | exact |
| M5 audited deletion | **1.000** (pre-delete visibility 1.000) | 1.000 | 1.000 | 0.500 | 1.000 | 1.000 | exact (governed tombstone) |
| M6 LLM portability | **not comparable** | — | — | — | — | — | no executable upstream protocol |

`n/c`: not comparable, because LLM-extracting systems rewrite memory text. The answer-substring diagnostic only counts verbatim answer strings, so it favours systems that store text verbatim (Agent Memory, Naive RAG) over systems that paraphrase it. It is a lower bound on judged recall: on the published files it reports a judged miss as a hit for at most 0.2% of rows. It is not a ranking of the systems. The fair diagnostic contrast is Agent Memory against Naive RAG, the two verbatim stores: 0.728 vs 0.794 on answer substring and 0.899 vs 0.971 on source text. Agent Memory's lexical-only retrieval trails bge-m3 dense retrieval on paraphrased queries.

### M4 failure taxonomy (250 pairs, classifier 1.2.0, `upstream_consistency: true`)

| Stage condition | Met | Unmet |
| --- | ---: | ---: |
| write admission (both writes committed) | 250 | 0 |
| candidate generation (new fact is a candidate) | 250 | 0 |
| admission (new fact admitted) | 250 | 0 |
| write interpretation (both propositions known) | 250 | 0 |
| identity / slot resolution (same slot) | 250 | 0 |
| conflict / supersession reasoning (`state_change_candidate` with proposal, basis `single_valued_replacement_marker`) | 250 | 0 |
| temporal applicability / currentness separates the pair | **0** | **250** |
| ranking puts the new fact first | 50 | 200 |

- Every one of the 200 stale results has the primary stage `temporal_applicability_currentness`.
- The decisive ranking stage is `lexical_relevance_desc:bm25_admitted_set:lexical` in all 250 pairs.
- All 50 new-fact wins are the `preference` template, with `win_basis = lexical_ordering`. Not one is a currentness win.
- The other four templates (`location`, `role`, `status`, `numeric`) are stale in 50 of 50 pairs each.

The mechanism, read from the per-case evidence:

1. Every query resolves to explicit current intent (`query_language_explicit`, cue "current"/"currently").
2. Every new write is interpreted as the same slot as the old one, and the write-time classifier attaches an explicit, unhedged `state_change_candidate` relation with a correction proposal.
3. Both facts carry `temporal_applicability = unknown_temporal_basis`. The new write's "now" is recorded as an aspect marker but yields no interpreted self-validity.
4. The explicit-current pairwise constraint (`temporal_order_constraints.build_explicit_current_constraints`) only builds applicable-over-unknown edges, so it reports `not_in_exclusive_competition`. The open proposal is never applied: proposals apply only through governed `AgentMemory.correct(...)`.
5. Ordering therefore falls to BM25 relevance, which favours the old template in four of the five categories.

**Interpretation for the architecture.** The 0.20 / 0.80 adapted signal persists unchanged under the formal protocol. The failure is not interpretation, identity, candidate generation or admission: Agent Memory already detects the state change at write time in every case. The gap is the step between the write-time semantics and read-path currentness. A detected, explicit, unhedged state change by the subject's own new statement does not change the old fact's currentness status, and it does not produce an applicability basis the read path can use.

This is #671's capability work. It must close the gap without making recency authoritative (newer != superseding) and without auto-applying proposals outside governance. Upstream M4 also rewards relevance accidents: Naive RAG scores 1.000 with no currentness machinery. So an M4 improvement only counts as currentness capability when the classifier attributes it to `currentness_mechanism`.

### Determinism

A second execution at the executed revision `7b041a7`, in a separate worktree on the same pristine upstream, reproduced the run exactly:

- retrieval: every retrieved item's sha256;
- M4: every case's outcome, primary stage, win basis and decisive stage;
- conflict, isolation and deletion: every non-latency field;
- scale: recall@3;
- the M2 diagnostics.

The raw report that the judge needs can therefore be regenerated deterministically. Regeneration must run at `7b041a7`. The runner refuses any later revision, because the evidence import added an integration record under `reference/agentmem_ref/evaluation`, which is inside the bound runtime tree.

### Classification summary (#694 completion terms)

| Axis | Result class |
| --- | --- |
| M1 | executed; write success, concurrency success exact; latency/throughput environment-bound |
| M2 | executed; judged recall **blocked** (credential); diagnostics adapted |
| M3 | executed; exact recall; latency environment-bound |
| M4 | executed; exact; per-case failures retained and stage-classified |
| M5 | executed; exact |
| M6 | not comparable (no upstream protocol) |

Actual performance deficits:

- **M4 currentness**, a runtime composition gap between write-time semantics and read-path currentness (#671);
- **M2 retrieval breadth on paraphrased queries**: diagnostic only until judged, and consistent with the unreachable semantic vector route (#669).

Evidence gaps:

- M2 judged recall (no authorized judge);
- same-harness reproduction of the five comparators (published reference only);
- latency in an equivalent environment.

Not comparable:

- M6.

### Replay plan for post-runtime milestones

Re-run the same frozen runner, unchanged, after every material runtime tranche that touches retrieval, ranking, interpretation or currentness. The runtime tree and policy binding in the freeze then differ, and that difference is the point: a new freeze with only the `agent_memory` block updated is a successor identity. Report:

- the delta for each axis against this baseline;
- the M4 `win_basis` and `primary_stage` distributions, not only the rate.

Judged M2 runs once an authorized Qwen2.5-14B-Instruct judge exists. It re-judges this baseline's raw report and the five published upstream detail files with the same judge.
