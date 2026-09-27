# #583 external replay: policy 3.0.2 (lexical/intent separation) vs frozen policy 3.0.1

Evidence class: external benchmark evidence (AgentMemBench / MemDialogue v2, LongMemEval_S),
bounded to these corpora and this retrieval profile. It is not proof of general superiority
or correctness. ADR-039 remains **Proposed**.

**Disposition: HOLD.** #587 stays draft. AgentMemBench supports the candidate, but LongMemEval_S
shows that removing the cues costs retrieval and currentness on natural data. Every one of
those losses is attributable to the intended mechanism, and none is unexplained drift. The
same data shows that the premise "these cues are intent-only" does not hold for the corpus
(see [Finding](#finding-the-intent-only-premise-does-not-hold-on-natural-data)).

## Identities

| item | value |
|---|---|
| main | `009a7372f5aae5c6daf980edcf55c18d06db6616` (PR #581) |
| candidate | `1b422680257a4f1f953180cbeb7386133ca893ee` (#587), ranking policy 3.0.2, interpreter 1.0.0 |
| canonical 3.0.1 evidence | `reports/benchmarks/replays/576-deterministic-bm25/*8bd6c91*` (runtime at `8bd6c91` equals `009a737` except `evaluation/temporal_currentness.py`, which the benchmarks do not import) |
| AgentMemBench | `mazaiying/AgentMemBench@186c9a54edd47aae42d8b6990520f8e902b60303`; `data/memdialogue_v2.jsonl` sha256 `33632710ae6495b95724df455ff6f9947d231ee68ebc0ef10eb8291fd55ca2a6`, 7,663,311 bytes (real payload, not an LFS pointer); harness `unified_benchmark.py` sha256 `d0d40712…94df` |
| LongMemEval_S | `xiaowu0162/longmemeval-cleaned@98d7416c24c778c2fee6e6f3006e7a073259d48f` `longmemeval_s_cleaned.json` sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, 277,383,467 bytes, 500 questions; upstream `xiaowu0162/LongMemEval@9e0b455f` |

Both inputs were acquired once and verified against the canonical reports before any run. The
LongMemEval_S replay for #578 (`1ea4d93`) ran in the same tranche against the same bytes (see `batched-578-1ea4d93/`).

## AgentMemBench (all phases, seed 2027, PYTHONHASHSEED 0 and 1)

* `compare-agentmembench-1b42268-seed{0,1}-vs-8bd6c91.json`: **0 non-timing differences** in every
  dimension and in the governance tallies. Exact-source recall 0.899 (PERSONAL_FACT 0.962, TASK_REQUEST 0.836),
  conflict new-fact 0.20 / staleness 0.80 / dual 0.0, cross-user leak 0.0, audited deletion 1.0,
  concurrency 1.0 success, no phase errors.
* Control: `009a737` under the same tracer reproduces the canonical `8bd6c91` search order and BM25 digests exactly.
* Per-search trace (`agentmembench-traces/`, texts as digests only): 2,051 searches; 116 had a cue excluded
  (`currently` 101, `plan to` 11, `planning to` 3, `intend to` 1); **10 changed order**, all retrieval-phase
  queries with a prospective cue excluded (`agentmembench-rank-differences-1b42268-vs-8bd6c91.json`):
  * 0 changes without an excluded cue; seed 0 and seed 1 traces are identical;
  * gold rank unchanged in 9; improved 2 -> 1 in 1 (record 618); 0 exact-source-hit changes;
  * in every change the demoted memories contain the removed cue tokens (`plan`/`planning`/`intend`/`to`)
    and the promoted ones contain fewer or none. BM25-only recomputation reproduces 9/10 orders exactly;
    the 10th (search 784) is a bit-exact tie that the cue removal creates, broken by the declared
    `candidate_ref_neutral_digest` fallback;
  * the 100 conflict-phase `currently` queries do not change: the stale fact still wins, through length
    normalisation. #583 alone does not affect the proposition-identity deficit (#550).

Classification: 10 x INTENDED_583_EFFECT. No NUMERICAL_ONLY, UNRELATED_DRIFT, FAILURE_OR_GOVERNANCE_CHANGE, or UNEXPLAINED.

## LongMemEval_S (session + turn planes, all 3 backends, 3,000 rows)

`compare-lme-s-1b42268-vs-8bd6c91.json`, `lme-s-query-attribution-1b42268.json`, `lme-s-affected-question-outcomes-1b42268.json`.

* Affected population: 23/500 questions have a cue excluded (`currently` 15, `planning to` 5, `plan to` 1,
  `going to` 1, `next week` 1; 11 knowledge-update). The remaining 477 questions are **row-identical** in
  both planes. no_memory / lexical_overlap are identical. Governance, failures, authority effect, and
  boundary are identical; there are no admission, refusal, or ingestion changes.
* 34 changed rows (session 18, turn 16), **all INTENDED_583_EFFECT** (the question had a cue excluded, and
  only `ranked_top` / `metrics` / `latest_gold_first` changed). 0 NUMERICAL_ONLY, 0 UNRELATED_DRIFT,
  0 FAILURE_OR_GOVERNANCE_CHANGE, 0 UNEXPLAINED.
* Per affected question: session plane 1 metric loss, 1 gain, 16 rank-only, 5 identical. Turn plane 5 losses
  (one also loses latest-gold-first), 2 gains, 9 rank-only, 7 identical.

| metric (agent_memory) | 3.0.1 | 3.0.2 delta |
|---|---:|---:|
| session headline (ndcg/recall @5/@10) | unchanged | 0 |
| session recall_any@1 | | -0.0024 (89941a93) |
| turn ndcg_any@5 / @10 | 0.6486 / 0.6816 | -0.0048 / -0.0031 |
| turn recall_all@5 / @10 / @50 | 0.6014 / 0.7232 / 0.8592 | -0.0048 / 0 / 0 |
| turn knowledge-update recall_all@5 / ndcg_any@5 | | -0.0139 / -0.0113 |
| latest-gold-ranked-first, session (70 applicable) | 0.457 | 0 |
| latest-gold-ranked-first, turn (70 applicable) | 0.557 | **-0.014** (07741c45: True -> False) |

Changed rows with a metric change:

| row | cue | gold ranks 3.0.1 -> 3.0.2 | gold contains cue | cause |
|---|---|---|---|---|
| turn 86f00804 | currently | 1 -> 8 | yes ("I'm currently devouring …") | the cue was the gold's own self-description |
| turn 07741c45 (KU) | currently | 2,6 -> 4,6; latest-first lost | the latest gold does | the current-state turn loses its only currentness signal |
| session 89941a93 (KU) | currently | 1,3 -> 2,3 | no | the other session's cue credit is removed; the relative order flips |
| turn eace081b (KU) | planning to | 4 -> 7 | yes ("I'm actually planning to stay on Oahu") | a prospective cue that is the answer content |
| turn cf22b7bf (KU) | going to | 1,3 -> 1,4 | no | the query is "started going to the gym", a motion verb that interpreter 1.0.0 reads as prospective/high |
| turn a9f6b44c | plan to | 2,8,14 -> 5,7,12 | no | "service or plan to service": the plan is the queried event |
| turn 46a3abf7, both planes gpt4_194be4b3 | currently | small gains (ndcg@10-50 +0.005) | no | intended: non-gold memories lose cue credit |

Wall time: 944 s vs 1,078 s canonical. No cost regression.

## Finding: the intent-only premise does not hold on natural data

The candidate is behaving as specified. The loss follows from the specification:

1. **`currently` is not intent-only when memories are first-person self-descriptions.** In 6 of the 19
   affected questions that have gold, a gold turn contains the excluded cue. Before #550 exists, lexical
   overlap on `currently` is the only signal that carries a memory's temporal self-description. Removing it
   fixes F30 in the repository-owned gauntlet but costs a latest-gold-first and a rank-1 gold on real data.
   This supports the #580 finding that self-description needs a governed, typed carrier (#550). It also
   challenges the sequencing "#583 before #550": the proxy should be replaced, not only removed.
2. **Prospective phrases are frequently content-bearing** (`planning to stay`, `plan to service`), and
   `going to` is also a motion verb. The `_RELEVANCE_INTENT_ONLY_CUES` classification is wrong for these on
   this corpus. The `going to` case is also an interpreter calibration defect (#585): "started going to the
   gym" is not prospective intent.
3. **No #583-bounded remediation clears the gate.** Exclusion is query-side and per question, so any cue
   subset's outcome follows row by row from this replay. Keeping only `currently` would still carry the
   86f00804 (1 -> 8), 07741c45 (latest-first lost), and 89941a93 losses against two small gains. Dropping
   `currently` as well removes the F30 fix entirely.

## LongMemEval_M

Not run. The formal escalation triggers (a currentness regression and a small retrieval regression) are met,
but M would not change the decision. M shares S's 500 questions, so the affected query population cannot
grow, and the candidate is already held on S. M becomes necessary for any revised candidate that still moves
currentness on S.

## Batched #578 (`1ea4d93`, policy 3.0.1)

`batched-578-1ea4d93/compare-lme-s-1ea4d93-vs-8bd6c91.json`: **IDENTICAL**. 3,000/3,000 rows are semantically
identical, with 0 rank differences, same input sha256, and no version-string changes. Recorded here only
because it shares the acquisition. PR #578 itself is not modified.
