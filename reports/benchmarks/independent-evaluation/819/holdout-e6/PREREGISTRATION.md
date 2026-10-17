# e6 preregistration: arms, comparisons and qualification gates

This file is fixed before any new candidate is examined (see `COMMITMENT.md`). The arms, metrics, gates and tools below do not change after a candidate is seen. A candidate that cannot be run under them is reported as not evaluable, never re-scored under a changed protocol.

## Environment (pinned)

- **Host and interpreter:**
  - Linux 6.18.44 microVM with 4 vCPU and 15 GiB RAM.
  - CPython 3.13.16. One venv per runtime, built from that runtime's own `reference/requirements.txt` and `reference/requirements-semantic.txt`, then `pip install --no-deps -e`. Each venv's `pip freeze` is recorded.
- **Process environment:**
  - `PYTHONHASHSEED=0` and `HF_HUB_OFFLINE=1`.
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `HF_TOKEN` are unset.
  - No paid inference and no network during runs. No GitHub Actions.
- **Semantic model:** `sentence-transformers/multi-qa-MiniLM-L6-cos-v1@b207367332321f8e44f96e224ef15bc607f4dbf0`. It is fetched once by the runtime's own pinned fetcher, which verified all `PINNED_FILES` digests (`onnx/model.onnx` `826501e8…`).
- **LongMemEval-S input:** `longmemeval_s_cleaned.json`, sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, the same file as the lane's earlier runs.

## Arms

| # | Runtime | Semantic route | Return selection | Purpose |
|---:|---|---|---|---|
| 1 | C4 `bc2be631` | off | default | default lineage |
| 2 | C4 | `required` | default | essential comparator (C4+sem) |
| 3 | C6 `171e67db` | `required` | default | current semantic selection (C6+sem) |
| 4 | **D**: isolated discovery candidate | as declared | as declared | candidate |
| 5 | **S**: isolated selection candidate | as declared | as declared | candidate |
| 6 | D, route off / declared default | off | default | equivalence with its declared lineage, if it declares one |
| 7 | S, route off / declared default | off | default | equivalence with its declared lineage, if it declares one |
| 8 | D and S repeat runs | as arms 4 and 5 | as arms 4 and 5 | determinism |

**What counts as a candidate:**
- A candidate is the exact immutable SHA that its engineer posts on #819 as **frozen for independent evaluation**.
- Its configuration is the one stated in its freeze record. It is passed only through `harness.py --semantic/--open-kwargs/--recall-kwargs`, unchanged.
- A candidate that changes the public facade so that the sealed harness cannot drive it is reported as not evaluable.
- No candidate implementation is modified by this lane.

**If a candidate declares several configurations:**
- The **default route** is primary.
- A non-default route, such as `ranked_prefix`, is diagnostic only and is never used for a verdict.

## Primary metrics (e6, budget 5)

1. **Selected-evidence recall@5.** The mean over answer-bearing queries of returned needed memories divided by needed memories.
2. **Strict case correctness**, as defined in `COMMITMENT.md`.
3. **False-positive inclusion.** The share of queries returning anything outside the needed and allowed sets, or anything excluded.
4. **Abstention.** Correct abstention on no-answer queries, and false abstention on answer-bearing queries.

**Secondary metrics:**
- Discovery and admission rates of needed memories, with the per-stage loss taxonomy (`not_discovered`, `refused:*`, `withheld_in_top_k`, `admitted_below_budget`).
- Depth recall@{1, 3, 5, 10}.
- Per-family breakdowns.
- Recall latency.

**Statistics** (`e6_analyze.py`):
- Exact two-sided McNemar on per-query binaries.
- Paired percentile bootstrap 95% CIs on per-query mean differences, with 10,000 resamples and seed 819.

**Primary pairs:**
- Each candidate against C4+sem (arm 2), C6+sem (arm 3) and C4 default (arm 1).
- D against S, descriptively.

## Qualification gates

All gates must hold before this lane recommends integration.

- **G1, user-visible gain.**
  - **Required gain.** Against C4+sem, at least one of these improves significantly:
    - selected-evidence recall@5, with the bootstrap 95% lower bound above 0;
    - strict, with candidate-only wins exceeding base-only wins at exact McNemar p < 0.05.
  - **Non-inferiority.** Against each of C4+sem, C6+sem and C4 default:
    - recall@5 has a 95% lower bound of at least −0.02;
    - strict is not significantly worse, meaning not (losses > wins with p < 0.05).
  - **What does not count.** Ranking-depth gains without returned-evidence gains do not count.
- **G2, false positives and abstention.** Against C6+sem, false-positive inclusion and correct abstention are not significantly worse. Against C4+sem, false abstention is not significantly worse. "Significantly worse" means exact McNemar p < 0.05 in the harmful direction.
- **G3, safety, a hard gate.** There are zero leaks on e6: no forgotten, disputed, error-corrected, superseded, as-of successor or other-scope memory is returned or quoted. One leak fails the gate.
- **G4, LongMemEval-S 500.**
  - **Runner.** The candidate runs on runner blob `6b9c237380f1d527e564161c2dac7fe32ada0ef9` (`reference/run_longmemeval.py`) with `--granularity session --granularity turn`, using its declared semantic setting.
  - **No significant loss.** Exact McNemar p < 0.05 with full-recall losses exceeding wins counts as a loss. This applies to `recall_all@3`, `@5` and `@10`, on either plane, against each of C4 default, C4+sem and C6+sem.
  - **Reporting.** `@50` is reported.
  - **Comparators.** These are the lane's committed outputs from the same runner and input, with sha256 of the raw JSON:
    - C4 default `c16d890f…`;
    - C4+sem `7107e37b…`;
    - C6+sem `c3645ff0…`.

    C4 default is re-run on this host to confirm reproduction.
  - **Tool.** `tools/lme_paired_e6.py`.
- **G5, cost.**
  - **Measurement.** Warm recall p95 at 400–500 admitted memories under the default route, measured as described below.
  - **Limit.** At most 1.15× C6+sem at the same N.
  - **Also reported:** p50, cold first recall, peak RSS and 200 admitted.
  - **No silent fallback.** Any size cutoff or fallback must be visible in the candidate's posture or return policy.
- **G6, determinism.** The repeat run returns identical lists on 288 of 288 cases. A route-off or default-lineage arm that the candidate declares equivalent must be identical to that lineage on 288 of 288.

**Verdicts:**
- If G1 fails, the verdict is **STOP / CHANGES REQUIRED**, naming the failing stage from the loss taxonomy.
- If G3 fails, the verdict is **CHANGES REQUIRED** regardless of other gains.

## Cost probe

`tools/latency_e6.py`, sha256 `591770b9247c83413bde2bd98cdeb7e86a5a2e23666320442da082662f1973e6`, is public and synthetic, not cohort content.

- **Sizes:** N ∈ {200, 400, 450, 500}.
- **Repetitions:** 2, run sequentially.
- **Arms:** 1, 2 and 3, plus each candidate under its declared configuration.

## Other evaluator tools

| File | SHA-256 |
| --- | --- |
| `tools/lme_paired_e6.py` | `7cc56d7cd79e7aa69a58d3eb94de9b78f9138b9f6fea1fbaa4f7a636e23d6d8a` |
| `tools/run_logged.py` (from the lane, unchanged) | `42af7fb8205d1040d241af90b48559e64de403da6ef2d28f156935465dd0c9a6` |

## Separation from candidate engineers

- **What this lane publishes before the final verdict:**
  - this preregistration and the commitment;
  - execution receipts and result-file hashes;
  - public-benchmark (LongMemEval) and synthetic-cost results.
- **What it does not publish:** no e6 case, label, per-case result, per-category result or diagnosis derived from e6, for any arm, baselines included.
- **No tuning advice.** It offers no tuning suggestions derived from e6.
- **No promotion.** It promotes no leaderboard row, register entry or feed item.
