# e4 results for C6: aggregates relayed by the cohort author

- **Sender:** the independent evaluation session `session_01FtboyaoG7RJJk5JnYpH24t`. It authored e4 and committed its hashes at `81b02a25` (22:49:20Z), before C6 was checked out.
- **Channel:** `send_message` to `session_011h1ADQyj3ZTu9UHgBAhocF`, queued 2026-10-15T23:24:35Z.
- **Recipient:** this session does not hold the cohort and has not re-run it. The figures below are the sender's, reproduced verbatim.
- **Scorer:** `harness.py` sha256 `805d76b1…`, byte-identical to v1–v3. Cases `976f1f9d…`. Budget 5. The semantic arms set `semantic_retrieval="required"` and `representation_dir` through the open-defaults wrapper (`run_with.py`) that the e4 commitment preregistered; the scorer bytes were unchanged.
- **Runtimes, per the sender's run script:**
  - A: `amb-venv-base` at `7c06468a`;
  - C4: `amb-venv-c4` at `bc2be631`;
  - C4+sem: `amb-venv-c4sem`;
  - C6-off and C6+sem: `amb-venv-c6sem` at `171e67db`.
- **Semantic environments:** exact pins onnxruntime 1.30.0, tokenizers 0.23.2, numpy 2.4.6. The model was fetched with C6's checksum-verifying fetcher, and its config digest `sha256:74477054…` was verified in both semantic venvs.
- **Host:** shared with Cognee generation 2 and Jev-Mem runs, so latencies are indicative only.

## Verbatim relay

> The e4 holdout is complete (holdout-done). Aggregates only, no cohort content; 208 queries, budget 5, scorer 805d76b1, cases 976f1f9d:
>
> - Strict pass (all with 0 eval failures and 0 cross-scope / forgotten / stale leaks): A 30, C4 128, C6-off 128 (identical to C4 on all 208), C4+sem 133, **C6+sem 144**.
> - Mean recall: C4 0.773, C4+sem 0.947, C6+sem 0.879.
> - Mean precision: C4 0.727, C4+sem 0.792, C6+sem 0.853.
> - Recall latency p50: C4 58 ms, C4+sem 753 ms, C6+sem 759 ms. Shared host with Cognee gen-2 and Jev-Mem running.
> - Paired:
>   - C4 → C6+sem: +16/−0, p = 3.1e-5.
>   - C4+sem → C6+sem: +24/−13, p = 0.099; Δ recall −0.068 [−0.099, −0.041].
>   - A → C6+sem: +114/−0; Δ recall +0.010 [−0.028, +0.049].
> - By category, strict pass (recall) for A / C4 / C4+sem / C6+sem:
>   - paraphrase 0 (0.50) / 0 (0.00) / 16 (1.00) / 16 (1.00);
>   - multi-evidence aggregation 0 (0.56) / 0 (0.00) / 7 (0.73) / 0 (0.17);
>   - multi-hop (bridge lexically disjoint) 0 (0.50) / 0 / 6 (0.69) / 0 (0.50);
>   - multi-session 0 / 24 / 7 / 24;
>   - disambiguation 0 / 8 / 4 / 8;
>   - factual 0 / 16 / 14 / 16;
>   - corrected 2 / 16 / 15 / 16;
>   - conflicting newer-first 0 for all;
>   - abstention, isolation, irrelevant and currentness: C4, C4+sem and C6+sem all 16.

The sender's raw summary line for the C6+sem arm, from its run log:

> `c6-sem {"queries": 208, "strict_pass": 144, "eval_failures": 0, "mean_precision": 0.8532, "precision_n": 176, "mean_recall": 0.8788, "recall_n": 176, "isolation_leaks": 0, "forgotten_leaks": 0, "stale_returned": 0, "mean_returned": 1.0} {"p50": 758.905, "p95": 956.061, "max": 1239.997}`

## What is not here, and why

- **Per-case e4 rows and the sealed package** (generator, scorer, cases, wrapper and raw results). The author declined to publish them on a peer-session request and asked its owner to confirm, because publication is irreversible.
- **A content-free per-case file** (case id, category and per-arm metrics, with no query or memory text) was offered as a middle ground. It is also gated on that owner's decision.
- **e4 is spent** once these aggregates are published. It must not be reused for tuning or for qualifying a later candidate.
