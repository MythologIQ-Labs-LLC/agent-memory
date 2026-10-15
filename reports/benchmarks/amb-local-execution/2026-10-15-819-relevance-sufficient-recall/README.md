# #819 candidates: relevance-sufficient recall selection

This is **candidate** evidence, not accepted evidence. Nothing here changes the canonical
leaderboard, the Runtime Baseline register, or any frozen lane. Every run was local; no hosted
CI ran and no PR is open. The independent evaluator for #819 has both candidate SHAs and runs
its hidden holdout separately.

| Item | Value |
|---|---|
| **C2** (recommended) | `eaf60e4dd001c02ce00bb36f15f800996bf77da3`: selection policy 1.1.0 |
| **C1** | `4bd38e6ca9cec9de7a054dd6b970ac26f05fb946`: selection policy 1.0.0 |
| **A** (baseline) | `1df28f84c236f5369b004465252610bd88ae07c9`. Its runtime is identical to the #818-evaluated `7c06468` (`git diff 38f6a7dc 7c06468 -- reference/agentmem_ref` is empty) |
| Preregistration | `5079c3d5` (`PREREGISTRATION.md`): design and `rho = 0.5`, fixed before any candidate ran |
| Held-out seal | `34c38e5d` (`HELDOUT-SEAL.md`): hashes recorded before the cohort was read or run |
| C2 addendum | `9611fd41` (`PREREGISTRATION-ADDENDUM-C2.md`): review-driven fixes, committed before any C2 run |
| AMB | `vectorize-io/agent-memory-benchmark` `03c1d0f1d27da63034f0931121c858faba512383`, PrecisionMemBench single-turn, retrieval mode, no LLM. Bridge 0.4.0 blob `3d9ccb3` is unchanged. Fixtures `35659b3b…` and `09e99f08…` |
| LongMemEval | `longmemeval_s_cleaned.json`, sha256 `d6f21ea9…c3a442` (hub `98d7416c`), all 500 questions, budget 50, frozen runner unmodified |

## Phase 1: what was wrong

`TRACE.md` traces every query, with 20 failures analysed case by case, through the public
`AgentMemory.recall`.

- **Cause.** The lexical route admits any fact that shares *any* token with the query, function
  words included. No stage between ranking and the budget asks whether a fact has enough
  evidence to be returned. So `returned` was `min(k, admitted)` facts however weak the match:
  17 of 72 queries returned the full 20.
- **What was not the cause.**
  - Admission refused nothing.
  - Temporal stages never acted.
  - Scope, type and lifecycle never reached the runtime. AMB furnishes them only to
    filter-capable providers or as prose.
- `TRACE.md` classifies each cause as faulty implementation, missing functionality, absent
  context, or protocol limitation.

## Phase 2: the change

`AgentMemory.recall` now runs a **return selection** stage between ranking and the budget. It is
the default. The code is `reference/agentmem_ref/runtime/return_selection.py`, documented as
contract `1.9.0` in `docs/44-public-api-contract.md`.

1. **Informative query terms** are the ranking tokens after contraction normalisation, minus a
   closed-class English function-word list. A function word the query writes as a name ("Will",
   "May", "US") still counts, except in all-caps or title-case queries.
2. **Content relevance** is BM25 over informative terms only. It reuses the ranking stage's
   admitted-set statistics, lexical scope and #583 anti-laundering masks.
3. A fact is **sufficient** if any of these holds:
   - it is an exact-identity hit;
   - a non-lexical route surfaced it;
   - its content relevance is at least 0.5 of the best in the recall;
   - (1.1.0) it has topical evidence and ranks above a sufficient fact.
4. If no fact is sufficient, the recall **abstains** and returns nothing.
5. `returned` is the sufficient facts in ranked order, then the budget.
6. Candidates, admission, refusals, `admitted` and ranking order are unchanged. Each decision is
   recorded in `admissions[ref].return_selection` with `authority_effect: none`.
7. `recall(..., return_selection="ranked_prefix")` gives the contract 1.4.0 behaviour exactly.

No benchmark ID, category, expected answer or dataset field appears in the runtime. The AMB
bridge is untouched.

**C1 → C2.** An independent adversarial review of C1 (summarised below) found two defects.
Both were reproduced on hand-written memories:

- a fact stuffed with query terms could displace the top-ranked fact;
- the stop list hid names and content words such as "Will", "May", "US", "like" and "Vitamin D".

C2 fixes both. It changes no case outcome on AMB or on the held-out set.

## Phase 3: results

### AMB native scorer, 77 cases (diagnostic only: these cases informed the design)

Source: `paired/paired-amb-c{1,2}.*`, produced by `scripts/compare_amb_paired.py`.

| Metric | A | C1 | C2 | C2 − A (95% paired bootstrap CI) |
|---|---:|---:|---:|---|
| Strict case success | 15/77 | 39/77 | **39/77** | +0.312 [+0.208, +0.416] |
| Active / structural / trivially-empty | 4/43, 6/25, 5/9 | 21/43, 12/25, 6/9 | 21/43, 12/25, 6/9 | |
| Mean precision | 0.1806 | 0.5415 | **0.5407** | +0.360 [+0.266, +0.457] |
| Mean recall | 0.9535 | 0.8782 | 0.8782 | −0.075 [−0.149, −0.016] |
| Mean documents returned | 8.92 | 1.36 | 1.38 | |

**Paired, A → C2: 24 fixed, 0 broken** (exact McNemar p = 1.2e-7). C1 → C2: 0 case changes.

| Category | Cases | A | C1/C2 |
|---|---:|---:|---:|
| Alias resolution | 23 | 3 | 14 |
| Budget eviction and capacity | 5 | 3 | 5 |
| Scope disambiguation | 12 | 0 | 3 |
| Fuzzy matching and prefix guards | 7 | 3 | 5 |
| Persona prelude content | 4 | 1 | 3 |
| Ranking stability | 3 | 1 | 3 |
| Design boundary cases | 6 | 2 | 3 |
| Relation expansion | 4 | 0 | 1 |
| Cross-user isolation / Cold start | 1 / 1 | 1 / 1 | 1 / 1 |
| Counter-signal retrieval | 2 | 0 | 0 |
| Supersession chain exclusion | 3 | 0 | 0 |
| Type routing and open questions | 6 | 0 | 0 |

Run integrity:

- A reproduces the #818 evidence file with 0 case differences.
- For each candidate, repetitions 1 and 2 agree on every score, relevant belief and failure set.
- The comparator still reports 6 field differences between repetitions. All are the order of
  names inside AMB's `judge_reason` strings: the scorer iterates a Python `set`, so the order
  follows the hash seed.

**B (structured filter) was not run.** AMB's `retrieval_filter` is built from tags that an
extraction LLM writes at ingest (`name:*`, `state:*`). Agent Memory stores no such tags, so equal
furnishing would need new bridge capability.

### Held-out cohort, 70 cases (same native scorer)

The cohort was authored by a separate agent instructed not to read this repository's code or
fixtures (`heldout/cohort/AUTHORING.md`). It has 59 beliefs across home, finance and health,
including:

- name collisions;
- supersession chains;
- relations;
- open questions;
- paraphrases.

It was sealed before first use, and C1 was its first candidate run. C2 came later and is not
blind on it.

| Metric | A | C1 | C2 | C2 − A (95% CI) |
|---|---:|---:|---:|---|
| Strict case success | 0/70 | 14/70 | **14/70** | +0.200 [+0.114, +0.300] |
| Mean precision | 0.0453 | 0.2755 | 0.2744 | +0.229 [+0.146, +0.321] |
| Mean recall | 0.7752 | 0.6221 | 0.6376 | −0.138 [−0.239, −0.052] |
| Mean documents returned | 17.97 | 2.69 | 2.99 | |

**Paired, A → C1 and A → C2: 14 fixed, 0 broken** (McNemar p = 1.2e-4).

- **Recall cost.** The drop exceeds the 0.10 bound preregistered for AMB. Every case that lost
  recall is one where A returned 19 beliefs, a third of the corpus.
- **Isolation.** No run surfaces another user's belief.
- **Still failing.** Out-of-scope 0/6, name-collision 0/5, multi-belief 0/4 and relation 0/3.

### LongMemEval-S retrieval regression profile

Sources: `longmemeval/*-summary-*.json` (from `scripts/summarize_longmemeval_return_selection.py`)
and the gzipped native reports. The `ranked_prefix` rows come from
`scripts/run_longmemeval_return_selection.py`, which fixes the keyword without editing the pinned
runner blob.

| Plane, metric | A | C1 default | C2 default | C1/C2 `ranked_prefix` |
|---|---:|---:|---:|---:|
| session recall_any@1 | 0.8091 | 0.8138 | 0.8138 | 0.8091 |
| session recall_all@5 | 0.8234 | 0.7422 | 0.7470 | 0.8234 |
| session recall_all@10 | 0.8926 | 0.7494 | 0.7542 | 0.8926 |
| session ndcg_any@10 | 0.8783 | 0.8237 | 0.8237 | 0.8783 |
| session mean returned | 45.06 | 2.59 | 3.02 | 45.06 |
| turn recall_any@1 | 0.5728 | 0.5823 | 0.5776 | 0.5728 |
| turn recall_all@5 | 0.6014 | 0.5585 | 0.5489 | 0.6014 |
| turn recall_all@10 | 0.7232 | 0.6158 | 0.6325 | 0.7232 |
| turn ndcg_any@10 | 0.6816 | 0.6562 | 0.6532 | 0.6816 |
| turn mean returned | 50.0 | 5.12 | 7.31 | 50.0 |

- **`ranked_prefix` reproduces A exactly** on all 500 questions, in every metric and every
  `ranked_top`, on both planes, for C1 and for C2. Ranking is untouched.
- **The default selection is an operating point, not a free win.**
  - Top-1 improves.
  - Single-evidence question types are unchanged or better (session single-session-user
    recall_any@1 0.843 → 0.857).
  - Multi-evidence types lose depth. Session recall_all@10:
    - multi-session 0.827 → 0.632 (C2);
    - temporal-reasoning 0.895 → 0.707;
    - knowledge-update 0.987 → 0.910.
  - On the 30 abstention questions, the mean returned drops from 45.3 to 3.7 (session, C2).

## Correctness and safety

- **Full suite.** `python -m unittest discover -s reference/tests -t reference` from the repo
  root:

  | Run | Tests | Result |
  |---|---:|---|
  | A | 2561 | all pass |
  | C1 | 2580 | 1 failure |
  | C2 | 2585 | 1 failure |

  The single failure in C1 and C2 is `test_evaluation_only_change_keeps_runtime_baseline_equivalence`
  (`suite/`). That test is the Runtime Baseline gate. It fails by design for any runtime change
  without a declared successor. Declaring one mutates the baseline register: that is an owner
  decision, and it has to come after the v8 security stack's successor.
- **New regression tests** (24 in `reference/tests/test_relevance_sufficient_return_selection.py`)
  cover:
  - function-word-only matches are admitted but not returned;
  - abstention;
  - the relative floor;
  - exact-identity and non-lexical bypass;
  - ranked-order subsequence with the budget applied after selection;
  - `ranked_prefix` equal to 1.4.0;
  - determinism;
  - other-scope facts never surfaced;
  - forgotten facts never returned;
  - corrected values replacing superseded ones;
  - the review repros (stuffed fact; "Who is Will?", "in May", "What do I like?");
  - contraction handling.
- **Unchanged suites.** Currentness, cross-fact, correction, forgetting, isolation, canonical-truth
  and Gauntlet durability suites pass without modification.
- **Tests edited.** Edits are limited to the contract version number, the next-minor probe
  (`1.10.0`), and two LongMemEval runner tests that asserted `returned` was the full ranked
  prefix.
- **Validators.** `validate_architecture_index`, `validate_doctrine_boundaries` and
  `validate_schemas` pass.
- **Independent adversarial review of C1.** Verdict: no blocking defect.
  - No governance bypass across other scopes, `correct()`-superseded facts or forgotten facts,
    under either selection, budget `None` and `1`.
  - `ranked_prefix` is byte-identical to 1.4.0 over 12 queries × 4 budgets, including
    admissions and decision ids.
  - The #583 masks hold against self-claiming memory text.
  - Output is deterministic across six PYTHONHASHSEED values.
  - Two should-fix defects were reported; both are fixed in C2.
  - Open notes from that review:
    - memory text that claims supersession in words the write classifier does not detect can
      still outrank, and now withhold, a canonical fact (see Limitations);
    - `1.7.0`/`1.8.0` envelopes report `current` here.
- **Why governance cannot be weakened.**
  - The stage runs after admission and only removes facts from `returned`.
  - Isolation, forgetting, correction and currentness are decided earlier and are untouched.
  - Every withheld fact stays in `admitted`.

## Why it should generalize

The mechanism uses no dataset vocabulary:

- function words are a closed grammatical class;
- the floor is scale-free (relative to the best match within the same recall, route and
  statistics);
- abstention follows from "no informative term matched".

It improved the diagnostic set and a disjoint, independently authored cohort with zero paired
regressions on either, and it improved LongMemEval top-1. Its weakness is equally general and
appears on all three datasets: **queries that need several pieces of evidence with unequal
lexical support lose the weaker ones.**

## Limitations that remain

1. **Multi-evidence recall.** This is the main cost. It shows as:
   - LongMemEval recall_all@10: −0.14 session, −0.09 turn (C2);
   - held-out multi-belief 0/4;
   - the AMB cap-stress cases.

   Rank-depth consumers should use `ranked_prefix`. **Whether selection is the default is an
   owner decision** that trades depth recall for context precision.
2. **Scope.** The query-only bridge carries no scope, so same-name collisions across scopes
   remain:
   - AMB scope disambiguation 3/12;
   - held-out out-of-scope 0/6;
   - held-out name collisions 0/5.
3. **Type and lifecycle stated only in prose.** Open questions, resolutions and text-only
   supersession are not recognised (AMB type routing 0/6, supersession 0/3). Canonical
   `correct()` supersession is still excluded. Memory text that claims to replace other memories,
   in words the write classifier misses, can now cause the canonical fact to be withheld rather
   than merely outranked.
4. **No typo or morphology tolerance.** `typsecript`, `mongod` and `moongoose` still miss.
5. **Semantic route.** With semantic retrieval on, vector candidates are never withheld, so the
   precision gain applies to the default lexical posture only.
6. **Contract number.** `1.9.0` must be reconciled with the v8 stack's `1.7.0`/`1.8.0`.
   `1.7.0`/`1.8.0` envelopes are reported `current` here, but those minors' behaviour is absent.
7. **Not independently confirmed yet.** These results are self-measured. The #819 independent
   evaluator's hidden holdout (160 scenarios, 176 queries) has not reported yet.

## Reproduce

```bash
# AMB environment exactly as in ../2026-10-15-precisionmembench-single-turn/README.md
python scripts/run_amb_local_evidence.py --amb-root $AMB --python $VENV/bin/python \
  --evidence-dir out/C2 --set-env TIKTOKEN_CACHE_DIR=$TT --set-env HF_HUB_OFFLINE=1 \
  -- run --dataset precisionmembench --split single-turn --memory agent-memory --mode retrieval
# held-out: add --set-env PRECISIONMEMBENCH_DATA_PATH=<this dir>/heldout/cohort
python scripts/compare_amb_paired.py A/.../single-turn.json C2/.../single-turn.json --markdown paired.md
python reference/run_longmemeval.py --input longmemeval_s_cleaned.json --corpus-class external_frozen \
  --granularity session --backend agent_memory --agent-memory-budget 50 --output C2.json
python scripts/run_longmemeval_return_selection.py ranked_prefix -- <same arguments> --output C2rp.json
python scripts/summarize_longmemeval_return_selection.py session --baseline A.json --candidate C2.json \
  --ranked-prefix C2rp.json --output summary.json
python scripts/trace_pmb_recall.py reference $AMB/.datasets/precisionmembench trace.json
python -m unittest discover -s reference/tests -t reference
```
