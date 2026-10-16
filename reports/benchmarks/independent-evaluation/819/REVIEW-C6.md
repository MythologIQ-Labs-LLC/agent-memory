# #819 independent evaluation: C6 (rank-bounded semantic proposals)

**Recommendation: CHANGES REQUIRED.**

C6 makes C4's optional semantic route useful for paraphrase. It does that by capping the route, and the cap gives back the reach that #819 most needs.

- **With the route on, against C4 default (off):** C6 is a real gain. On the e4 cohort it scores +16 / −0 (p = 3.1e-5), and paraphrase goes from 0 to 16 of 16.
- **Against C4 with the route on:** C6 gains precision and loses recall. Every dataset agrees on the recall loss: the hidden e4 cohort, LongMemEval-S, this evaluator's probes, and the developer's own development and reviewer sets.
- **Aggregation is the main casualty.** On e4, multi-evidence aggregation recall is 0.17 for C6 against 0.73 for C4+sem. That is the defect C3/C4 review required change 1 asked to fix, and C6 with the route on leaves it where C4 default had it.
- **The failed preregistered prediction stands.** The preregistration expected recall against C4+sem to stay level or rise. It fell on every dataset, and the cause is identified below. The strict-pass gain does not cancel the loss: on e4 it is not significant (p = 0.099), and on the probes it reverses (p = 0.035).
- **No safety, determinism or route-off problem was found.**

{{LME_SUMMARY}}

| Item | Value |
| --- | --- |
| Baseline A | `7c06468aae1aed0d2115c42f9588fbbe8417657e` |
| C4 | `bc2be6319a3eda96731fdb235f4feba882bcb9be` |
| C6 (frozen) | `171e67db041434e1144dd83a73423af6d4c267e1`, tree `6986b8f1`, `reference/` tree `d587e3e6` |
| C6 policy | `rank-bounded-semantic-proposals` 1.0.0: `min_best` 0.40, `margin` 0.20, `k_single` 1, `k_set` 3; applies under `relevance_sufficient` only |
| Semantic configuration | `semantic_retrieval="required"`, `multi-qa-MiniLM-L6-cos-v1@b207367`, config digest `sha256:74477054…1dd31aee` (reproduced on both hosts) |
| Libraries | onnxruntime 1.30.0, tokenizers 0.23.2, numpy 2.4.6, protobuf 7.36.2 (`requirements-semantic.txt` exact pins). Python 3.12.3 on both evaluator hosts; the developer used 3.13.16 |
| Runner and bridge blobs | `run_longmemeval.py` `6b9c2373`, `amb_agent_memory_bridge.py` `3d9ccb31`, `run_amb_external.py` `0c7b4383`, `amb_retrieval_no_llm.py` `1d3584f0`. Identical across A, C4 and C6 |
| Evaluators | e4 was authored and run by the independent evaluation session `session_01FtboyaoG7RJJk5JnYpH24t`. LongMemEval, probes, latency, determinism and this review are by `session_011h1ADQyj3ZTu9UHgBAhocF`, which took over the lane at 23:13Z. Neither session contributed to C6 |

## Provenance and the lane handover

The C6 evaluation started in one session and is finished in another:

- **First session.** It authored the e4 cohort and committed its hashes in `holdout-e4/COMMITMENT.md` (commit `81b02a25`, 22:49:20Z). That was before C6 was checked out or `FREEZE-C6.md` was read. It then ran the five-arm e4 matrix to completion. At 23:12Z the owner moved that session to #810.
- **This session.** It started in a fresh container with no access to the first session's files. It never saw the e4 cohort.
- **The first session's LongMemEval queue** was cancelled at about 23:20Z, before any run had started. The LongMemEval results below are therefore the only C6 and C4+sem runs.
- **e4 aggregates** were relayed from the first session at 23:24Z (`candidates/c6-171e67d/e4/RELAYED-AGGREGATES.md`). With its owner's approval, that session then pushed a text-free per-case record (`holdout-e4/handoff/e4-percase-textfree.json`, sha256 `227f472a…`, commit `bdbd8a63` on `claude/819-independent-evaluation-no-ci`). The record holds per-arm metrics for each of the 208 cases, with no query or memory text. Its `MANIFEST.txt` shows `sha256sum -c` OK against the `81b02a25` hashes, the wrapper hash, the runtime HEADs, the pip freezes and the host state.
- **This session recomputed every e4 statistic below from that per-case record** (`candidates/c6-171e67d/e4/e4_paired.py` → `e4-paired.json`, the same method as `tools/paired.py`). The results match the relayed aggregates exactly.
- **This session did not re-run e4.** The cohort content stays sealed with its author.

## 1. Hidden cohort e4: 208 queries, five preregistered arms

The arms follow the preregistered order: A, C4 default, C4+sem, C6+sem, C6 with the route off. All five completed with 0 evaluation failures, 0 operation refusals, 0 cross-scope leaks, 0 forgotten leaks and 0 stale returns. Figures are recomputed from the per-case record.

| | A | C4 | C6 off | C4+sem | **C6+sem** |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strict pass (of 208) | 30 | 128 | 128 | 133 | **144** |
| Mean recall | — | 0.773 | = C4 | 0.947 | 0.879 |
| Mean precision | — | 0.727 | = C4 | 0.792 | 0.853 |
| Recall latency p50 (shared, loaded host) | — | 58 ms | — | 753 ms | 759 ms |

**Route off equals C4 on every recorded field.** That covers strict pass, precision, recall, returned count, leaks and failures, for all 208 cases.

Paired results, recomputed from the per-case record (bootstrap 10,000 resamples, seed 819):

| Pair | Wins / losses | Exact McNemar p | Δ strict rate | Δ recall | Δ precision (both returned) |
| --- | --- | ---: | --- | --- | --- |
| C4 → C6+sem | +16 / −0 | 3.1e-5 | +0.077 [+0.043, +0.115] | +0.106 [+0.066, +0.150] | +0.126 [+0.080, +0.175] |
| **C4+sem → C6+sem** | **+24 / −13** | **0.099** | +0.053 [−0.005, +0.111] | **−0.068 [−0.099, −0.041]** | +0.003 [−0.031, +0.035] |
| A → C6+sem | +114 / −0 | < 1e-6 | +0.548 [+0.481, +0.615] | +0.010 [−0.027, +0.049] | +0.368 [+0.306, +0.428] |
| C4 → C4+sem | +29 / −24 | 0.58 | +0.024 [−0.043, +0.091] | +0.174 [+0.124, +0.228] | +0.123 [+0.067, +0.183] |

**Every C6 loss to C4+sem is reach, and every win is precision.** All 13 losses are in aggregation (7) and multi-hop (6). All 24 wins are in multi-session (17), disambiguation (4), factual (2) and corrected (1).

Where both runtimes return something, C6's mean precision is no better than C4+sem's (Δ +0.003). Its strict wins come from returning fewer extras on distractor-dense stores, which shows in strict pass and mean returned count (1.00 against 1.33), not in per-case precision.

By category, strict passes (recall in brackets):

| Category | A | C4 | C4+sem | C6+sem |
| --- | --- | --- | --- | --- |
| Paraphrase | 0 (0.50) | 0 (0.00) | 16 (1.00) | **16 (1.00)** |
| **Multi-evidence aggregation** | 0 (0.56) | 0 (0.00) | **7 (0.73)** | **0 (0.17)** |
| **Multi-hop (bridge lexically disjoint)** | 0 (0.50) | 0 (0.50) | **6 (0.69)** | **0 (0.50)** |
| Multi-session (of 32) | 0 | 24 | 7 | 24 |
| Disambiguation | 0 | 8 | 4 | 8 |
| Factual precision | 0 | 16 | 14 | 16 |
| Corrected memory | 2 | 16 | 15 | 16 |
| Conflicting, newer first | 0 | 0 | 0 | 0 |
| Abstention, isolation, irrelevant, currentness | — | 16 each | 16 each | 16 each |

What the table shows:
- **C6's 11-pass lead over C4+sem is a precision effect.** It comes from multi-session (+17), disambiguation (+4), factual (+2) and corrected (+1), where uncapped proposals flooded the return.
- **C4+sem's wins are reach.** Aggregation (+7) and multi-hop (+6) are cases where C6 returns too little.
- **The strict difference is not significant**, while the recall loss is (the CI excludes 0).

**Cohort status: e4 is spent.** Its aggregates are now published. Cohort content stays with its author.

{{LME_SECTION}}

## 3. Independent adversarial probes (57 queries, evaluator-authored)

**Set.** Written by this session after reading C6's diff and freeze record, known limits included, and before any e4 or LongMemEval result was seen. The content is in neither e4 nor the developer's fixtures.

**The set is adversarial by design.** It targets the dimensions this review was asked to challenge, including C6's stated limits. It is not a representative sample, so its rates must not be read as population rates. Its value is in the mechanisms it exposes and in the direction of its paired comparisons. It has 56 fresh stores, budget 5, the real pinned model and the public facade. The categories are:
- aggregation (8);
- paraphrase (8);
- no-answer beside a semantic near-miss (8);
- question-shaped slot capture (7);
- list questions the plural reading may miss (10, including one control and one false-positive probe);
- historical and as-of recall (6);
- cross-scope (4);
- forgotten, corrected and disputed memories (6).

Files: `candidates/c6-171e67d/probes/`, with the builder, harness, per-case outputs and `SHA256SUMS`.

| | A | C4 | C6 off | C4+sem | **C6+sem** |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strict (of 57) | 3 | 22 | 22 | 33 | **24** |
| Needed memories returned (of 69) | 30 | 14 | 14 | 53 | **29** |
| Extras | 116 | 4 | 4 | 13 | 7 |
| Excluded memory returned | 2 | 0 | 0 | 1 | 0 |
| No-answer queries returning something (of 8) | 7 | 2 | 2 | 5 | 5 |

Paired results:
- **C4+sem → C6+sem:** +3 / −12, p = 0.035. Per-query recall change −0.325 [−0.454, −0.196].
- **C4 → C6+sem:** +5 / −3, p = 0.73. Recall +0.196 [+0.096, +0.308].
- **C4 → C6 off:** identical on all 57 queries.

**Why C6 loses to C4+sem.** Each of the 20 queries where the two differ was traced to the proposal policy. Cosines come from the route's own provenance. The full table is in `probes/out/`.

| Mechanism | Queries | Example (true-answer cosine) |
| --- | ---: | --- |
| **`min_best` = 0.40.** The best match is below 0.40, so nothing is proposed. Under this model, true paraphrase and aggregate answers often score 0.30 to 0.40 | 9 | "Which medicines am I on?" (0.37, 0.33, 0.32); "When did my spouse and I get married?" (0.40−); "What do I collect?" (0.30) |
| **K = 1 because the set reading misses.** Only one member of a set is proposed | 6 | "Remind me of everything I'm allergic to." (0.47, 0.42, 0.41); "Name the cities I've travelled to."; "Tell me about my siblings."; "Where have I lived?"; "Tell me the instruments I play."; "Any pets in the wider family?" |
| **Question-shaped slot capture.** A note that repeats the question takes the single slot. The relative margin would cut the answers even at K = 3 | 2 | "What should I get Mum for her birthday?": note 0.98, answer 0.50. "Which plants need repotting?": note 0.87, answers 0.44 and 0.34 |
| **Pool filter and `min_best` together.** The superseded original is the best match, and the pool correctly drops it. The successor's 0.335 is then below `min_best` | 1 | "What's my diet like these days?" |
| **C6 better: no absolute floor below the best match** | 1 | Aggregate member at 0.277 reached (`agg1`) |
| **C6 better: precision** (the cap avoids an extra) | 2 | `qshape4`, `list10` |

The probes and e4 disagree on strict pass because their stores differ. The probe stores are sparse, with 6 fillers and 1 to 3 relevant memories, and there C4+sem's wide proposals cost few extras. e4's multi-session and disambiguation stores are dense with distractors, and there they cost precision. The recall loss is the same in both.

## 4. Adversarial review by dimension

| Dimension | Finding | Evidence |
| --- | --- | --- |
| **Multi-evidence aggregation** | **Fails.** e4 recall 0.17 (C4+sem 0.73), 7 of the 13 e4 losses; probe aggregation 8 of 23 needed (C4+sem 18 of 23). The cap (K = 3, margin 0.20, `min_best` 0.40) and the set reading together withhold most aggregate members | §1, §3 |
| **Paraphrase retrieval** | **Succeeds on e4** (16/16, the same as C4+sem). On the probes it gets 4/8 against C4+sem's 7/8, losing three paraphrases scored 0.33 to 0.40 to `min_best` | §1, §3 |
| **No-answer abstention** | **No improvement over C4+sem.** It returns something on 5 of 8 probe no-answer queries, against 5 of 8 for C4+sem and 2 of 8 for C4 default. Every case is a near-miss above 0.40 ("sister's favourite film" against "brother loves Star Wars"). e4 abstention is 16/16 for all three. `min_best` measures topical closeness, not answerability (the preregistered limit) | §3 |
| **Question-shaped slot capture** | **Confirmed** (known limit 1). Two probe losses. The relative margin also narrows the window for plural questions | §3 |
| **List-question detection** | **Confirmed** (known limit 2). Missed: "Which animals live with us?", "Which people do I mentor?", "Which of my friends…", "Where have I lived?", "What do I collect?", "Tell me…", "Any pets…", "Name the…", "everything I'm…". False positive: "What glasses do I wear?" reads as plural; the margin limited the harm. The reading is a closed English grammar with no recovery path | §3; `return_selection.plural_answer` |
| **Historical and as-of** | **C6 is correct.** Its mode-aware pool filter keeps refused memories out of the slot: forgotten, error-corrected and disputed memories in historical recall. **Pre-existing, all runtimes:** as-of recall also returns a successor whose `valid_from` is after the as-of date. A, C4, C4+sem and C6, route on or off, all do this. Old-first ordering is correct. Temporal intent only orders, by design (ADR-039, proposed), so no as-of query can be strict. Not attributable to C6 | `probes2.json`, `out/p2-*.json` |
| **Cross-scope exclusion** | **Holds.** Other-scope near-duplicates were never returned and their text never appeared in any result: 0 reference leaks and 0 text leaks, also on e4. A store binds one tenant and refuses to open under another, so the route cannot cross tenants within a store (fail-closed). `scope3` fails for every runtime, because "Who is on call this week?" never retrieves "Beta's on-call engineer…". That is a recall miss, not a leak | §3 |
| **Forgotten, corrected and disputed** | **Holds in current-state recall.** No forgotten, superseded or disputed memory was returned or quoted. `life4` shows the pool filter's one cost: it removes the strongest anchor, so `min_best` then fails on the successor | §3 |
| **Determinism** | **Holds.** Two fresh C6+sem probe runs are identical, proposals and cosines included. Across hosts, the developer's C6, C4+sem and C4-off returned lists replicate 55/55 on this host under Python 3.12.3 (developer: 3.13.16), and their proposal cosines are identical at the harness's 3-decimal resolution | §6 |
| **Latency and resources** | **C6 adds nothing over C4+sem. The route itself is costly** | §5 |
| **Network** | **No egress.** `strace -e connect,sendto` over a semantic-on run records 0 calls. The proxy logged telemetry attempts to `mobile.events.data.microsoft.com`; they came from the container environment and are not attributable to Agent Memory | — |

## 5. Latency and resource cost (this host, controlled)

The store holds N generated memories. Each run does 1 cold recall, then 40 warm ones. Files: `probes/latency.py`, `probes/out/lat-*.json`. One LongMemEval run was using about one core of four throughout.

| N | Arm | Ingest | First recall (cold) | Warm p50 | Warm p95 | Peak RSS | Store size |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 200 | C4 | 1.2 s | 28 ms | 20 ms | 29 ms | 38 MiB | 1.27 MB |
| 200 | C4+sem | 2.0 s | 1,400 ms | 39 ms | 53 ms | 328 MiB | 1.74 MB |
| 200 | C6+sem | 1.6 s | 1,339 ms | 38 ms | 62 ms | 326 MiB | 1.72 MB |
| 1,000 | C4 | 6.0 s | 123 ms | 75 ms | 108 ms | 58 MiB | 4.7 MB |
| 1,000 | C4+sem | 6.6 s | 6,623 ms | 174 ms | 219 ms | 330 MiB | 6.9 MB |
| 1,000 | C6+sem | 6.8 s | 6,620 ms | 165 ms | 200 ms | 330 MiB | 6.9 MB |

- **C6 meets G7.** Its overhead over C4+sem is nil or slightly negative, because it proposes fewer candidates.
- **The route itself costs:**
  - about 2× warm latency;
  - +290 MiB resident memory for the model;
  - +36 to +46% store size;
  - a cold first recall that grows linearly with the number of unembedded memories (1.3 s at 200, 6.6 s at 1,000). Memories are embedded at first recall, not at write.

  These are C4 route properties, not C6's. They matter for activation, not for qualifying C6's policy.

## 6. Reproducibility

- **e4 commitment:** `81b02a25`, before C6 was checked out (first session).
- **Route off equals C4:** e4 208/208 on every field (per-case record); probes 57/57 (this session); developer's reviewer set 55/55 (developer, and replicated here).
- **Determinism:**
  - two identical C6+sem probe runs;
  - developer runs replicated 55/55 across hosts and interpreters, for C6+sem, C4+sem and C4-off;
  - the developer reviewer set's aggregates reproduce exactly (C6: 16 strict, recall 0.500, 61 extras; C4+sem: 6, 0.655, 120; C4-off: 11, 0.276, 53).
- **C6's own tests:**
  - `test_c6_semantic_discovery` with `test_facade_recall_control`: 29 tests, all pass on C6 here.
  - On C4: the 5 fail-first tests fail, and the 12 governance tests pass.
- **Environment:** `candidates/c6-171e67d/provenance/ENVIRONMENT.md` records the HEADs, trees, blobs, model file hashes, config digest, dataset hash and host. The pip freezes differ only in the editable path.
- **Exec records:** `lme500/*.exec.json` carries argv, cwd, exit status, wall time, child CPU, peak RSS, environment and absent secrets.

## 7. Failures, exclusions and incomplete outputs

- **e4:** 0 evaluation failures, leaks or stale returns in all five arms (per-case record). The relayed run notes also show 0 operation refusals. The text-free per-case record is published; the sealed cohort (generator, cases and texts) is not, by its owner's decision.
- **LongMemEval:** {{LME_FAILURES}}
- **AMB PrecisionMemBench with the route on: not run, by design of the existing adapter.**
  - `amb_agent_memory_bridge.py` (`3d9ccb31`) calls `AgentMemory.open` without `semantic_retrieval` (lines 259 and 309). Its only optional open setting is `recall_control`, and `run_amb_external.py` exposes no flag or environment variable for it.
  - Measuring semantic-on AMB would need an adapter change or an open-defaults wrapper. Neither is approved for AMB, so no substitute protocol was created.
  - C6 with the route off equals C4 on every source tested, so C6's default AMB result is C4's: 39 of 77.
- **Probe op failures:** none. The first probe draft had one cross-tenant scenario, which the runtime refused to open (store tenant binding). It was replaced by a cross-principal scope case (`scope2`, same text, `user:other`) before any arm's results were read. That was the only change. The draft file was overwritten and is not preserved; `SHA256SUMS` hashes the set as run.
- **Host interference:**
  - e4 latencies come from a host shared with Cognee generation 2 and a Jev-Mem run, so they are indicative only.
  - Here, the two semantic LongMemEval runs overlapped from 23:45Z onwards, one core each of four. The two lexical runs also overlapped each other.

## 8. The failed prediction, evaluated

The preregistration (`3d202484`) expected that, against C4+sem, "recall stays the same or rises". It did not, on any dataset:

| Dataset | Author | C4+sem recall | C6+sem recall |
| --- | --- | ---: | ---: |
| Development union (in-sample) | Developer | 0.628 | 0.551 |
| Reviewer set (55) | Developer's reviewer | 0.655 | 0.500 |
| e4 (208, hidden) | Independent | 0.947 | 0.879 [Δ CI −0.099, −0.041] |
| Probes (57) | Independent | 0.768 | 0.420 [per-query Δ CI −0.454, −0.196] |
| LongMemEval-S (session / turn) | Public | {{LME_PRED}} | |

**This is not an incidental trade-off.** The policy causes it:
- `min_best` sits above the cosine band where this model places true paraphrase and aggregate answers.
- K = 1 is applied whenever a closed grammar misses a set question.
- The margin is relative to whatever scores best, even a note that repeats the question.

**The gate could not catch it.** G1 bounds recall against C4 *default*, not against C4+sem. No gate criterion protected the reach C4+sem already had. The strict gains are real on distractor-dense data, but they are precision gains bought with reach. They do not offset a significant recall loss concentrated in the category #819 exists to fix.

## 9. Verdict and conditions

**CHANGES REQUIRED.** C6 is not rejected:
- it is safe, deterministic, network-free, and off by default;
- with the route off it is exactly C4;
- its paraphrase gain and its precision control are real.

It is not acceptable for integration qualification as frozen. The question was whether it makes semantic retrieval useful *without unacceptable recall loss*. It does not: the loss is significant on hidden data, and it falls on aggregation.

**Mandatory changes.** These belong in a new, separately preregistered candidate. C6's frozen parameters stay as they are, and none were adjusted after these results.

1. **Recall non-inferiority to C4+sem as a gate criterion.** On held-out data, the lower 95% bound of Δ recall must be ≥ −0.02, and aggregation recall must be ≥ C4+sem's. The current gate never compared recall to C4+sem.
2. **Aggregate and enumerative reach.**
   - Set-sized proposals must not depend only on the closed plural grammar. At a minimum, cover: "everything / all / any", "name / list / tell me", "which of", irregular plurals, implicit sets ("what do I collect", "where have I lived").
   - Alternatively, size K from the score distribution (a gap or cluster cutoff) instead of from query grammar.
3. **Replace the absolute `min_best` 0.40 anchor.** Under the pinned model, true answers often score 0.30 to 0.40. Abstention should rest on positive evidence of irrelevance (C4 review change 2), not on one absolute cosine.
4. **Question-shaped and meta notes must not anchor the margin.** Two options: exclude interrogative or meta notes from defining `best`, or stop one memory from both taking the only slot and narrowing the window.
5. **Interaction with the pool filter.** When the filter removes the strongest anchor (`life4`), the anchor test must use the remaining pool on its merits, not a threshold calibrated with superseded memories present.

**Governance conditions** (carried from the freeze record and C4):
- declare a Runtime Baseline successor covering the five protected files;
- rebase onto #805 `28f257c9` → #815 `77c472e6` → #816 `e13d8c58` and re-run the security replays;
- version the LongMemEval lane;
- correct `FREEZE-C6.md`. It says "The `ranked_prefix` default … unchanged", but the facade default is `relevance_sufficient` (`surface.py:264`), and C6's policy applies only there.

**Activation conditions.** These are not required for qualification, but they are required before the route could become a baseline default:
- embed at write time, or bound the cold first recall (6.6 s at 1,000 memories);
- an approved semantic-on AMB adapter option, so AMB can measure the route;
- disclose the +290 MiB resident cost.

**Acceptance criteria for the successor** (ACCEPTABLE FOR INTEGRATION QUALIFICATION):
- On a fresh independent sealed cohort:
  - strict non-inferior to both C4+sem and C4 default, by paired exact McNemar with no significant loss;
  - recall non-inferior to C4+sem, per change 1;
  - aggregation and paraphrase at least at C4+sem's level;
  - 0 leaks;
  - route off identical to the frozen default lineage.
- LongMemEval-S 500, session and turn: no significant loss against C4+sem or C4 default at recall_all@5 and @10.
- Determinism on two hosts.
- Warm p50 ≤ C4+sem + 10 ms.

Being acceptable for qualification would still not make the candidate an activated runtime baseline.

## 10. Cohort integrity

| Cohort | Status |
| --- | --- |
| v1, v2, v3 | Spent; earlier reviews published their aggregates |
| e4 | **Spent** with this review. Its content stays with its author, and it must not be used for tuning |
| v4 | Engineering's sealed cohort. **Remains reserved and unopened.** It was not used here |

- **The next candidate's cohort:** a fresh independent cohort is authored and its hashes committed only when that candidate is frozen and handed over, before its checkout.
- **Not for holdout use:** the developer's synthetic fixtures (dev sets and reviewer `gen.json`) are not used as independent holdouts. Here they served only as a determinism check.
- **The probes here are disclosed.** They count as development-visible from now on and must not be used as a holdout.
- **The probe text in this review is the evaluator's own.** It contains no e4 content.

This is an independent recommendation. It confers no acceptance and changes no register, dashboard, feed or leaderboard row.
